import torch
import torch.nn as nn
import torch.optim as optim
import requests
import os
import json
import numpy as np
from django.conf import settings
from .neo4j_db import neo4j_db

INTERACTION_SERVICE_URL = "http://interaction-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"

class LSTMRecommender(nn.Module):
    def __init__(self, num_users, num_products, num_actions, hidden_dim=32):
        super(LSTMRecommender, self).__init__()
        self.user_embedding = nn.Embedding(num_users, 16)
        self.book_embedding = nn.Embedding(num_products, 32)
        self.action_embedding = nn.Embedding(num_actions, 8)
        
        # LSTM input: Book embedding + Action embedding
        lstm_input_dim = 32 + 8
        self.lstm = nn.LSTM(lstm_input_dim, hidden_dim, batch_first=True)
        
        # Predictor combines User Emb + LSTM Hidden State to score candidate book
        predictor_input_dim = 16 + hidden_dim + 32
        self.predictor = nn.Sequential(
            nn.Linear(predictor_input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, user_ids, seq_books, seq_actions, candidate_books):
        # 1. Process Sequence
        b_embs = self.book_embedding(seq_books) # (batch, seq_len, 32)
        a_embs = self.action_embedding(seq_actions) # (batch, seq_len, 8)
        
        lstm_in = torch.cat([b_embs, a_embs], dim=2) # (batch, seq_len, 40)
        
        output, (h_n, c_n) = self.lstm(lstm_in)
        last_hidden = h_n[-1] # (batch, hidden_dim)
        
        # 2. Score Candidate
        u_emb = self.user_embedding(user_ids) # (batch, 16)
        cand_emb = self.book_embedding(candidate_books) # (batch, 32)
        
        combined = torch.cat([u_emb, last_hidden, cand_emb], dim=1) # (batch, 16 + 32 + 32)
        
        scores = self.predictor(combined)
        return scores.squeeze()

class BehaviorTrainer:
    def __init__(self, model_path="app/ai_core/behavior_model_lstm.pth"):
        self.model_path = model_path
        # Map actions to integers
        self.action_map = {"VIEWED": 1, "VIEW_PRODUCT": 1, "SEARCHED": 2, "CART": 3, "ADD_TO_CART": 3, "PURCHASED": 4}
        self.model = LSTMRecommender(num_users=5000, num_products=2000, num_actions=10)
        self.load()

    def load(self):
        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, weights_only=True))
                print(f"[MODEL] Loaded existing LSTM brain from {self.model_path}")
            except: 
                print("[MODEL] Failed to load LSTM model, starting fresh.")

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        print(f"[MODEL] Saved behavior model to {self.model_path}")

    def train_epoch(self, interactions, epochs=5):
        """
        Learns from (user_id, product_id, behavior_score, contextual_features)
        """
        import torch.optim as optim
        self.model.train()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        print(f"[MODEL] Neural Training started for {epochs} epochs...")
        
        for epoch in range(epochs):
            total_loss = 0
            for it in interactions:
                u_id = torch.tensor([int(it['user_id']) % 5000], dtype=torch.long)
                p_id = torch.tensor([int(it['product_id']) % 2000], dtype=torch.long)
                target = torch.tensor([float(it['behavior_score'])], dtype=torch.float)
                
                # For simplicity in this demo, we use a fixed empty sequence for legacy training
                # but real systems would use real interaction sequences from Interaction Service.
                seq_b = torch.tensor([[0]], dtype=torch.long)
                seq_a = torch.tensor([[0]], dtype=torch.long)

                optimizer.zero_grad()
                output = self.model(u_id, seq_b, seq_a, p_id)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            print(f"  > Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(interactions):.4f}")
        
        self.save()
        return True

    def get_sequential_recommendations(self, user_id, top_k=10):
        """
        Inference using LSTM and GraphRAG.
        1. Fetch recent sequence from Neo4j.
        2. Score all candidate books using LSTM.
        """
        import time
        self.model.eval()
        
        # 1. Get recent sequence from Neo4j
        interactions = neo4j_db.get_user_interactions(user_id, limit=10)
        
        seq_b = []
        seq_a = []
        for it in reversed(interactions): # chronological order
            p_id = int(it['product_id']) if str(it['product_id']).isdigit() else 0
            seq_b.append(p_id % 2000)
            seq_a.append(self.action_map.get(str(it['action']).upper(), 1))
            
        if not seq_b:
            # Need a pad if no history
            seq_b = [0]
            seq_a = [0]
            
        u_t = torch.tensor([user_id % 5000], dtype=torch.long)
        seq_b_t = torch.tensor([seq_b], dtype=torch.long)
        seq_a_t = torch.tensor([seq_a], dtype=torch.long)
        
        # 2. Get candidates (Cache strategy)
        try:
            r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=200", timeout=1)
            products = r.json().get('results', [])
        except:
            products = []
            
        if not products: return []

        p_ids = [int(p['id']) % 2000 for p in products]
        cands_t = torch.tensor(p_ids, dtype=torch.long)
        
        # 3. Batch Score via LSTM
        with torch.no_grad():
            # Expand u_t, seq_b_t, seq_a_t to match batch size
            batch_size = len(cands_t)
            u_batch = u_t.expand(batch_size)
            seq_b_batch = seq_b_t.expand(batch_size, -1)
            seq_a_batch = seq_a_t.expand(batch_size, -1)
            
            scores = self.model(u_batch, seq_b_batch, seq_a_batch, cands_t).tolist()
            if isinstance(scores, float): scores = [scores]

        # 4. Merge
        results = []
        for i, p in enumerate(products):
            results.append({
                'product_id': p['id'],
                'title': p.get('name', 'Unknown'),
                'score': round(scores[i], 2),
                'description': p.get('description', '')
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

# Singleton Instance
behavior_trainer = BehaviorTrainer()
