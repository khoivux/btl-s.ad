import torch
import torch.nn as nn
import torch.optim as optim
import requests
import os
import json
import numpy as np
from django.conf import settings

# --- API Endpoints ---
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
COMMENT_SERVICE_URL = "http://comment-rate-service:8006"

# --- NEW ARCHITECTURE (Context-Aware) ---
class TwoTowerModel(nn.Module):
    def __init__(self, num_users, num_books):
        super(TwoTowerModel, self).__init__()
        # User Tower: Embedding (8) + Context Features (5) = 13 dimensions
        self.user_embedding = nn.Embedding(num_users, 8)
        self.user_mlp = nn.Sequential(
            nn.Linear(8 + 5, 16),
            nn.ReLU(),
            nn.Linear(16, 16)
        )
        
        # Book Tower: Still 32-dim ID for now
        self.book_embedding = nn.Embedding(num_books, 32)
        self.book_mlp = nn.Sequential(
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 16)
        )

    def forward(self, user_inputs, book_inputs):
        # User side
        u_emb = self.user_embedding(user_inputs['id'])
        u_features = user_inputs['features']
        u_combined = torch.cat([u_emb, u_features], dim=1)
        u_vector = self.user_mlp(u_combined)
        
        # Book side
        b_vector = self.book_mlp(self.book_embedding(book_inputs['id']))
        
        # Dot product prediction
        return torch.sum(u_vector * b_vector, dim=1)

class BehaviorTrainer:
    def __init__(self, model_path="app/ai_core/behavior_model.pth"):
        self.model_path = model_path
        # Assuming 5000 users and 2000 books for safety
        self.model = TwoTowerModel(5000, 2000)
        self.load()

    def load(self):
        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, weights_only=True))
                print(f"[MODEL] Loaded existing brain from {self.model_path}")
            except: 
                print("[MODEL] Failed to load model, starting fresh.")

    def train_epoch(self, interactions, epochs=10):
        if not interactions:
            print("[TRAINER] No interaction data to train with.")
            return False
        
        import random
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        # Unique books for metrics
        all_books = list(set([it['book_id'] for it in interactions]))
        
        for ep in range(1, epochs + 1):
            random.shuffle(interactions)
            split_idx = int(len(interactions) * 0.7)
            train_data = interactions[:split_idx]
            val_data = interactions[split_idx:]
            
            # --- Training Phase ---
            self.model.train()
            train_loss = 0
            for item in train_data:
                optimizer.zero_grad()
                uid, bid, score = item['user_id'], item['book_id'], item['behavior_score']
                
                # Context Features from DataProcessor
                u_context = [item['f_recency'], item['f_freq'], item['f_spend'], item['f_rev_cnt'], item['f_cart_cnt']]
                
                u_in = {
                    'id': torch.tensor([int(uid) % 5000], dtype=torch.long),
                    'features': torch.tensor([u_context], dtype=torch.float32)
                }
                b_in = {'id': torch.tensor([int(bid) % 2000], dtype=torch.long)}
                
                pred = self.model(u_in, b_in)
                loss = criterion(pred, torch.tensor([score], dtype=torch.float32))
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            # --- Validation Phase ---
            self.model.eval()
            val_loss = 0
            prec_at_10, recall_at_10 = [], []
            
            # Group for metrics
            user_val_map = {}
            for item in val_data:
                u = item['user_id']
                if u not in user_val_map: user_val_map[u] = []
                user_val_map[u].append(item)
            
            with torch.no_grad():
                for item in val_data:
                    uid, bid, score = item['user_id'], item['book_id'], item['behavior_score']
                    u_context = [item['f_recency'], item['f_freq'], item['f_spend'], item['f_rev_cnt'], item['f_cart_cnt']]
                    u_in = {'id': torch.tensor([int(uid) % 5000], dtype=torch.long), 'features': torch.tensor([u_context], dtype=torch.float32)}
                    b_in = {'id': torch.tensor([int(bid) % 2000], dtype=torch.long)}
                    pred = self.model(u_in, b_in)
                    val_loss += criterion(pred, torch.tensor([score], dtype=torch.float32)).item()

                # P@10 & R@10 (Simplified for speed)
                for uid, actuals in list(user_val_map.items())[:20]: # Check up to 20 users for metrics
                    rel_items = set([it['book_id'] for it in actuals if it['behavior_score'] >= 4.0])
                    if not rel_items: continue
                    
                    profile = actuals[0] # Take first for context
                    u_context = [profile['f_recency'], profile['f_freq'], profile['f_spend'], profile['f_rev_cnt'], profile['f_cart_cnt']]
                    u_in = {'id': torch.tensor([int(uid) % 5000], dtype=torch.long), 'features': torch.tensor([u_context], dtype=torch.float32)}
                    
                    cands = random.sample(all_books, min(len(all_books), 100))
                    scores = []
                    for bid in cands:
                        b_in = {'id': torch.tensor([int(bid) % 2000], dtype=torch.long)}
                        s = self.model(u_in, b_in).item()
                        scores.append((bid, s))
                    
                    scores.sort(key=lambda x: x[1], reverse=True)
                    top_10 = set([x[0] for x in scores[:10]])
                    hits = len(top_10.intersection(rel_items))
                    prec_at_10.append(hits / 10)
                    recall_at_10.append(hits / len(rel_items))

            avg_train = train_loss / len(train_data)
            avg_val = val_loss / (len(val_data) or 1)
            avg_prec = (sum(prec_at_10) / len(prec_at_10)) if prec_at_10 else 0
            avg_recall = (sum(recall_at_10) / len(recall_at_10)) if recall_at_10 else 0
            
            print(f"[TRAINER] Ep {ep:02d} | Train L: {avg_train:.4f} | Val L: {avg_val:.4f} | P@10: {avg_prec:.4f} | R@10: {avg_recall:.4f}")

        return True

    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        print(f"[MODEL] Saved behavior model to {self.model_path}")

    def get_user_embedding(self, user_id, points=0, level_id=1):
        self.model.eval()
        with torch.no_grad():
            u_id_t = torch.tensor([user_id % 5000])
            feat_t = torch.tensor([[float(points), float(level_id)]], dtype=torch.float32)
            return self.model.user_tower(u_id_t, feat_t)

    def get_book_embedding(self, book_id, category_id=1, price=0.0):
        self.model.eval()
        with torch.no_grad():
            b_id_t = torch.tensor([book_id % 2000])
            c_id_t = torch.tensor([category_id])
            p_t = torch.tensor([float(price)], dtype=torch.float32)
            return self.model.book_tower(b_id_t, c_id_t, p_t)

    def get_user_live_context(self, user_id):
        """
        Fetches LIVE behavioral context for a user for real-time inference.
        """
        from .data_processor import data_processor
        import math
        
        # We need a simplified fetcher for just ONE user
        # For now, we can use the main processor's logic but scaled down
        # Ideally, we'd have a specific endpoint for user summary
        
        # Default stats for unknown/new users
        stats = {
            'f_recency': round(math.log1p(365), 4),
            'f_freq': 0.0,
            'f_spend': 0.0,
            'f_rev_cnt': 0.0,
            'f_cart_cnt': 0.0
        }
        
        try:
            # 1. Recency & Spend & Freq
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/?customer_id={user_id}", timeout=1)
            if r.status_code == 200:
                orders = r.json().get('results', [])
                if orders:
                    stats['f_freq'] = min(float(len(orders)), 50.0)
                    total_amt = sum([float(o.get('total_amount', 0)) for o in orders])
                    stats['f_spend'] = round(math.log1p(total_amt), 4)
                    
                    from datetime import datetime
                    now = datetime.now()
                    last_o = orders[0] # assuming sorted
                    o_date = datetime.fromisoformat(last_o['created_at'].replace('Z', '+00:00'))
                    days_ago = (now.astimezone() - o_date).days
                    stats['f_recency'] = round(math.log1p(max(0, days_ago)), 4)

            # 2. Reviews
            r_rev = requests.get(f"{COMMENT_SERVICE_URL}/reviews/all/", timeout=1)
            if r_rev.status_code == 200:
                all_revs = r_rev.json()
                u_revs = [rv for rv in all_revs if rv['customer_id'] == user_id]
                stats['f_rev_cnt'] = min(float(len(u_revs)), 20.0)

            # 3. Carts
            r_cart = requests.get(f"{CART_SERVICE_URL}/carts/{user_id}/", timeout=1)
            if r_cart.status_code == 200:
                stats['f_cart_cnt'] = min(float(len(r_cart.json())), 10.0)
        except: pass
        
        return stats

    # Local cache for book catalog to avoid repetitive API calls
    _cached_books = []
    _last_cache_time = 0

    def get_recommendations(self, user_id, top_k=10, category=None, max_price=None, author=None):
        """
        Ultra-Fast Vectorized Recommendation Engine.
        Scores all candidates in a SINGLE forward pass.
        """
        import time
        self.model.eval()
        
        # 1. Fetch Candidates (With simple 5-min caching)
        now_t = time.time()
        if not self._cached_books or (now_t - self._last_cache_time) > 300:
            try:
                r = requests.get(f"{BOOK_SERVICE_URL}/books/?page_size=200", timeout=1)
                if r.status_code == 200:
                    self._cached_books = r.json().get('results', [])
                    self._last_cache_time = now_t
            except: pass
        
        if not self._cached_books: return []

        # 2. Filter Candidates Locally (Super Fast)
        filtered_indices = []
        for i, b in enumerate(self._cached_books):
            if category and b.get('category_name') != category: continue
            if author and b.get('author') != author: continue
            if max_price and float(b.get('price', 0)) > float(max_price): continue
            filtered_indices.append(i)
        
        if not filtered_indices: return []

        # 3. Batch Context Preparation
        ctx = self.get_user_live_context(user_id)
        u_feat = [ctx['f_recency'], ctx['f_freq'], ctx['f_spend'], ctx['f_rev_cnt'], ctx['f_cart_cnt']]
        
        # Expand user data to match number of filtered books
        n_books = len(filtered_indices)
        u_ids_batch = torch.full((n_books,), int(user_id) % 5000, dtype=torch.long)
        u_feats_batch = torch.tensor([u_feat] * n_books, dtype=torch.float32)
        
        b_ids_list = [int(self._cached_books[idx]['id']) % 2000 for idx in filtered_indices]
        b_ids_batch = torch.tensor(b_ids_list, dtype=torch.long)

        # 4. ONE SINGLE FORWARD PASS (The Speed Demon!)
        with torch.no_grad():
            u_in = {'id': u_ids_batch, 'features': u_feats_batch}
            b_in = {'id': b_ids_batch}
            batch_scores = self.model(u_in, b_in).squeeze().tolist()
            
            # Handle single results where tolist() might return a float
            if isinstance(batch_scores, float): batch_scores = [batch_scores]

        # 5. Merge and Rank
        final_results = []
        for i, idx in enumerate(filtered_indices):
            book = self._cached_books[idx]
            final_results.append({
                'book_id': book['id'],
                'title': book.get('title', 'Unknown'),
                'score': round(batch_scores[i], 2),
                'category': book.get('category_name', 'Tech'),
                'price': book.get('price', 0),
                'author': book.get('author', 'Unknown'),
                'description': book.get('description', '') # ENRICHED DATA
            })
        
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:top_k]

# Singleton Instance
behavior_trainer = BehaviorTrainer()
