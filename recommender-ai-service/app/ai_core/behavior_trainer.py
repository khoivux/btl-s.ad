import torch
import torch.nn as nn
import requests
import os
import numpy as np
from django.conf import settings
from .neo4j_db import neo4j_db

PRODUCT_SERVICE_URL = "http://product-service:8000"

class SequenceRecommender(nn.Module):
    def __init__(self, num_products, num_actions, model_type='RNN', hidden_dim=128, num_layers=2):
        super(SequenceRecommender, self).__init__()
        self.model_type = model_type
        
        self.prod_emb = nn.Embedding(num_products + 1, 64)
        self.act_emb = nn.Embedding(num_actions + 1, 16)
        
        input_dim = 64 + 16
        self.is_bidirectional = (model_type == 'biLSTM')
        rnn_kwargs = {
            'input_size': input_dim, 
            'hidden_size': hidden_dim, 
            'num_layers': num_layers, 
            'batch_first': True,
            'dropout': 0.2 if num_layers > 1 else 0
        }
        
        if model_type == 'RNN':
            self.rnn = nn.RNN(**rnn_kwargs)
        elif model_type == 'LSTM':
            self.rnn = nn.LSTM(**rnn_kwargs)
        elif model_type == 'biLSTM':
            rnn_kwargs['bidirectional'] = True
            self.rnn = nn.LSTM(**rnn_kwargs)
            
        rnn_out_dim = hidden_dim * 2 if self.is_bidirectional else hidden_dim
        self.fc = nn.Sequential(
            nn.Linear(rnn_out_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_products)
        )
        
    def forward(self, x):
        p_seq = x[:, :, 0]
        a_seq = x[:, :, 1]
        
        p_emb = self.prod_emb(p_seq)
        a_emb = self.act_emb(a_seq)
        
        rnn_in = torch.cat([p_emb, a_emb], dim=-1)
        
        out, _ = self.rnn(rnn_in)
        last_out = out[:, -1, :]
        logits = self.fc(last_out)
        return logits

class BehaviorTrainer:
    def __init__(self, model_path="app/ai_core/behavior_model_best.pth", num_products=201):
        self.model_path = os.path.join(settings.BASE_DIR, model_path)
        self.action_map = {
            'view': 1, 'click': 2, 'add_to_cart': 3, 'remove_from_cart': 4, 
            'purchase': 5, 'wishlist': 6, 'review': 7, 'share': 8
        }
        self.num_products = num_products
        # We start with RNN as default, but load() might be called after training is DONE.
        # Ideally we should detect model type or just use the one that won.
        self.model = SequenceRecommender(num_products=num_products, num_actions=len(self.action_map), model_type='RNN')
        self.load()

    def load(self):
        if os.path.exists(self.model_path):
            try:
                # We need to knowing which model type was saved. 
                # For simplicity, if we suspect it might be LSTM after our recent talk, 
                # we'd need to adjust. But let's assume RNN for now as per previous run.
                # In a real system, we'd save metadata with the model.
                self.model.load_state_dict(torch.load(self.model_path, map_location=torch.device('cpu'), weights_only=True))
                print(f"[MODEL] Loaded best model from {self.model_path}")
            except Exception as e: 
                print(f"[MODEL] Failed to load model: {e}")

    def get_sequential_recommendations(self, user_id, top_k=10, cart_context=None):
        self.model.eval()
        seq_len = 10
        
        sim_boost = {}
        # 0. Integrated Real-time Cart Context into Social Boost (Graph)
        if cart_context:
            try:
                with neo4j_db.driver.session() as session:
                    # Look for items frequently bought with current items in cart
                    cart_sim_query = """
                    MATCH (pInCart:Product) WHERE pInCart.id IN $pids
                    MATCH (pInCart)<-[:INTERACTED_WITH]-(other:User)-[:INTERACTED_WITH]->(recProd:Product)
                    WHERE NOT recProd.id IN $pids
                    RETURN recProd.id as pid, count(other) as volume
                    ORDER BY volume DESC LIMIT 20
                    """
                    cart_recs = session.run(cart_sim_query, pids=[int(p) for p in cart_context])
                    for rec in cart_recs:
                        sim_boost[int(rec['pid'])] = sim_boost.get(int(rec['pid']), 0) + float(rec['volume']) * 2.0
            except Exception as e:
                print(f"[RECOM] Cart Neo4j context error: {e}")

        
        try:
            with neo4j_db.driver.session() as session:
                query = """
                MATCH (u:User {id: $uid})-[r:INTERACTED_WITH]->(p:Product)
                RETURN p.id as pid, r.action as action, r.timestamp as ts
                ORDER BY r.timestamp DESC LIMIT $limit
                """
                recs = session.run(query, uid=int(user_id), limit=seq_len)
                sequences = []
                for rec in recs:
                    p_id = (int(rec['pid']) - 1) % self.num_products
                    a_id = self.action_map.get(rec['action'], 0)
                    sequences.append([p_id, a_id])
                
                # Prepend cart context to sequence
                if cart_context:
                    context_seq = [[(int(pid)-1)%self.num_products, 2] for pid in cart_context]
                    sequences = (context_seq + sequences)[:seq_len]

                sequences = sequences[::-1]
                while len(sequences) < seq_len:
                    sequences.insert(0, [0, 0])
                
                seq_t = torch.tensor([sequences], dtype=torch.long)

        except Exception as e:
            print(f"[RECOM] Neo4j sequence fetch error: {e}")
            seq_t = torch.zeros((1, seq_len, 2), dtype=torch.long)

        with torch.no_grad():
            try:
                logits = self.model(seq_t)
                scores = torch.softmax(logits, dim=1).squeeze().tolist()
            except:
                scores = [0] * self.num_products

        # 2. Add Neighborhood Social Boost (Graph logic)
        try:

            with neo4j_db.driver.session() as session:
                sim_query = """
                MATCH (u:User {id: $uid})-[s:SIMILAR_TO]-(neighbor:User)-[:INTERACTED_WITH]->(p:Product)
                RETURN p.id as pid, sum(s.weight) as score
                ORDER BY score DESC LIMIT 50
                """
                sim_recs = session.run(sim_query, uid=int(user_id))
                for rec in sim_recs:
                    pid = int(rec['pid'])
                    sim_boost[pid] = sim_boost.get(pid, 0) + float(rec['score'])

        except Exception:
            pass

        try:
            r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=200", timeout=2)
            data = r.json()
            all_prods = data.get('results', []) if isinstance(data, dict) else data
        except Exception as e:
            print(f"[RECOM] Error fetching products in trainer: {e}")
            all_prods = []

        if cart_context:
            print(f"[RECOM] Cart Context items: {cart_context} | SimBoost entries: {len(sim_boost)}")

        results = []
        for p in all_prods:

            try:
                pid = int(p['id'])
                idx = (pid - 1) % self.num_products
                n_score = scores[idx] if idx < len(scores) else 0
                # Higher divisor for social boost to keep percentage reasonable
                s_boost = sim_boost.get(pid, 0) * 0.01 
                
                # Hybrid score capped at 0.99 for UI friendliness
                final_score = min(0.99, (n_score * 0.8) + (s_boost * 0.2))

                
                results.append({
                    'id': pid,
                    'title': p.get('name') or p.get('title'),
                    'price': p.get('price'),
                    'image_url': p.get('image_url'),
                    'score': float(final_score),
                    'final_score': float(final_score),
                    'social_proof': f"Gợi ý từ cộng đồng" if pid in sim_boost else "",
                    'description': p.get('description', '')
                })
            except Exception as e:
                print(f"[DEBUG-TRAINER] Error processing prod: {e}")

        print(f"[DEBUG-TRAINER] Generated {len(results)} ranked products.")
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results[:top_k]


# Singleton instance
behavior_trainer = BehaviorTrainer()
