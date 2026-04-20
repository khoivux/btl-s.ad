import requests
import json
from django.conf import settings
from ..ai_core.behavior_trainer import behavior_trainer

PRODUCT_SERVICE_URL = "http://product-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"

def get_recommendations(customer_id=None):
    """ 
    Intelligent Hybrid Recommendation Orchestrator.
    Prioritizes AI Behavioral Model for identified users.
    Falls back to Bayesian Global Ranking for guests.
    """
    
    # --- PHASE 1: AI NEURAL BRAIN (For Identified Users) ---
    if customer_id:
        print(f"[RECOM] 🧠 Activating 13-dim Neural Engine for User: {customer_id}")
        try:
            ai_recs = behavior_trainer.get_sequential_recommendations(customer_id, top_k=10)
            if ai_recs:
                # Format for frontend
                for r in ai_recs:
                    r['final_score'] = r['score']
                return ai_recs
        except Exception as e:
            print(f"[RECOM] ⚠️ AI Neural Engine Error: {e}. Falling back to legacy...")

    # --- PHASE 2: LEGACY BAYESIAN LOGIC (For Guests or Fallback) ---
    products = []
    try:
        r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=1000")
        if r.status_code == 200:
            data = r.json()
            products = data.get('results', []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[RECOM] Error fetching products: {e}")
        
    if not products: 
        return []

    # Calculate Bayesian Average for fallback
    all_ratings = [p.get('average_rating', 0) for p in products if p.get('reviews_count', 0) > 0]
    C = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    m = 1
    
    scored_products = []
    for product in products:
        v = product.get('reviews_count', 0)
        R = product.get('average_rating', 0)
        product['bayesian_score'] = (v / (v + m)) * R + (m / (v + m)) * C if v + m > 0 else 0
        product['final_score'] = product['bayesian_score']
        scored_products.append(product)

    scored_products.sort(key=lambda x: x['final_score'], reverse=True)
    return scored_products[:10]
