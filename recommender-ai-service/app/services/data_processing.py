import requests
import os
import pandas as pd
from django.conf import settings

# --- API Endpoints ---
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
COMMENT_SERVICE_URL = "http://comment-rate-service:8006"

class BehaviorDataProcessor:
    """
    Handles data engineering: Fetching raw data from and converting it to 
    (user_id, book_id, score) interactions for the ML model.
    """
    def fetch_raw_interactions(self):
        review_map = {} # (u, p) -> score
        order_map = {}  # (u, p) -> 5.0
        cart_map = {}   # (u, p) -> 3.0
        
        # User Context Buckets (for 5 features)
        user_orders_count = {}
        user_total_spend = {}
        user_last_order_date = {}
        user_review_count = {}
        user_cart_count = {}

        from datetime import datetime
        now = datetime.now()

        # 1. Orders & Spending & Recency
        print("[PROCESSOR] Fetching Orders & Contextual Stats...")
        try:
            url = f"{ORDER_SERVICE_URL}/orders/?page_size=100"
            while url:
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    for o in data.get('results', []):
                        u_id = o['customer_id']
                        val = float(o.get('total_amount', 0))
                        
                        user_orders_count[u_id] = user_orders_count.get(u_id, 0) + 1
                        user_total_spend[u_id] = user_total_spend.get(u_id, 0) + val
                        
                        try:
                            o_date = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                            days_ago = (now.astimezone() - o_date).days
                            if u_id not in user_last_order_date or days_ago < user_last_order_date[u_id]:
                                user_last_order_date[u_id] = days_ago
                        except: pass

                        r_items = requests.get(f"{ORDER_SERVICE_URL}/orders/{o['id']}/", timeout=1)
                        if r_items.status_code == 200:
                            for item in r_items.json().get('items', []):
                                order_map[(u_id, item['product_id'])] = 4.0 # ORDER IS 4.0
                    url = data.get('next')
                else: url = None
        except: pass

        # 2. Reviews & Sentiment Stats
        print("[PROCESSOR] Fetching Reviews...")
        try:
            r = requests.get(f"{COMMENT_SERVICE_URL}/reviews/all/", timeout=3)
            if r.status_code == 200:
                for rev in r.json():
                    u_id = rev['customer_id']
                    review_map[(u_id, rev['product_id'])] = float(rev['rating']) # REVIEW IS 1.0-5.0
                    user_review_count[u_id] = user_review_count.get(u_id, 0) + 1
        except: pass

        # 3. Carts & Interest Stats
        print("[PROCESSOR] Fetching Carts...")
        try:
            r_cust = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/?page_size=100", timeout=3)
            if r_cust.status_code == 200:
                data = r_cust.json()
                customers = data if isinstance(data, list) else data.get('results', [])
                for cust in customers:
                    cid = cust['id']
                    r_cart = requests.get(f"{CART_SERVICE_URL}/carts/{cid}/", timeout=1)
                    if r_cart.status_code == 200:
                        items = r_cart.json()
                        user_cart_count[cid] = len(items)
                        for c_item in items:
                            pid = c_item.get('product_id') or c_item.get('book_id')
                            if pid:
                                cart_map[(cid, pid)] = 2.0 # CART IS 2.0
        except: pass

        # --- CONSOLIDATION WITH LOG NORMALIZATION ---
        print("[PROCESSOR] Generating Normalized AI Dataset...")
        import math
        all_pairs = set(list(review_map.keys()) + list(order_map.keys()) + list(cart_map.keys()))
        
        final_list = []
        for pair in all_pairs:
            u_id, p_id = pair
            if pair in review_map: s = review_map[pair]
            elif pair in order_map: s = order_map[pair]
            else: s = cart_map[pair]
            
            # Context for this user
            rec = round(math.log1p(float(user_last_order_date.get(u_id, 365))), 4)
            fq = min(float(user_orders_count.get(u_id, 0)), 50.0)
            sp = round(math.log1p(float(user_total_spend.get(u_id, 0))), 4)
            rv = min(float(user_review_count.get(u_id, 0)), 20.0)
            ct = min(float(user_cart_count.get(u_id, 0)), 10.0)
            
            final_list.append({
                'user_id': u_id, 'product_id': p_id, 'behavior_score': s,
                'f_recency': rec, 'f_freq': fq, 'f_spend': sp, 'f_rev_cnt': rv, 'f_cart_cnt': ct
            })

        # --- NEGATIVE SAMPLING (Dạy AI cách từ chối) ---
        print("[PROCESSOR] Injecting Negative Samples (Dạy AI biết lắc đầu)...")
        import random
        all_product_ids = list(set([p[1] for p in all_pairs])) # Simple fallback
        try:
            r_products = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=100", timeout=3)
            if r_products.status_code == 200:
                all_product_ids = [p['id'] for p in r_products.json().get('results', [])]
        except: pass

        unique_users = set([p[0] for p in all_pairs])
        negative_list = []
        for u_id in unique_users:
            user_interacted = set([p[1] for p in all_pairs if p[0] == u_id])
            candidate_negatives = list(set(all_product_ids) - user_interacted)
            
            if candidate_negatives:
                selected_negs = random.sample(candidate_negatives, min(len(candidate_negatives), 3))
                for neg_p_id in selected_negs:
                    # Context for this user
                    rec = round(math.log1p(float(user_last_order_date.get(u_id, 365))), 4)
                    fq = min(float(user_orders_count.get(u_id, 0)), 50.0)
                    sp = round(math.log1p(float(user_total_spend.get(u_id, 0))), 4)
                    rv = min(float(user_review_count.get(u_id, 0)), 20.0)
                    ct = min(float(user_cart_count.get(u_id, 0)), 10.0)

                    negative_list.append({
                        'user_id': u_id, 'product_id': neg_p_id, 'behavior_score': 0.0,
                        'f_recency': rec, 'f_freq': fq, 'f_spend': sp, 'f_rev_cnt': rv, 'f_cart_cnt': ct
                    })

        final_list.extend(negative_list)
        print(f"[PROCESSOR] Exporting {len(final_list)} profiles ({len(negative_list)} Negatives included).")
        return final_list

    def save_to_csv(self, interactions, file_path="app/ai_core/behavior_dataset.csv"):
        """
        Exports to CSV with all 5 biographical features.
        """
        import pandas as pd
        if not interactions: return
        df = pd.DataFrame(interactions)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False)
        print(f"[PROCESSOR] 📁 Dataset saved at: {file_path}")

# Singleton Instance
data_processor = BehaviorDataProcessor()
