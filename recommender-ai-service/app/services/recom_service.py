import requests
import json
from django.conf import settings
from ..ai_core.behavior_trainer import behavior_trainer

BOOK_SERVICE_URL = "http://book-service:8000"
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
            ai_recs = behavior_trainer.get_recommendations(customer_id, top_k=10)
            if ai_recs:
                # Format to match legacy expectations if needed by templates
                for r in ai_recs:
                    r['id'] = r['book_id'] # alias
                    r['final_score'] = r['score']
                return ai_recs
        except Exception as e:
            print(f"[RECOM] ⚠️ AI Neural Engine Error: {e}. Falling back to legacy...")

    # --- PHASE 2: LEGACY BAYESIAN LOGIC (For Guests or Fallback) ---
    books = []
    try:
        r = requests.get(f"{BOOK_SERVICE_URL}/books/?limit=1000")
        if r.status_code == 200:
            data = r.json()
            books = data.get('results', []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[RECOM] Error fetching books: {e}")
        return []

    if not books: return []

    # Calculate Bayesian Average for fallback
    all_ratings = [b.get('average_rating', 0) for b in books if b.get('reviews_count', 0) > 0]
    C = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    m = 1
    
    scored_books = []
    for book in books:
        v = book.get('reviews_count', 0)
        R = book.get('average_rating', 0)
        book['bayesian_score'] = (v / (v + m)) * R + (m / (v + m)) * C if v + m > 0 else 0
        book['final_score'] = book['bayesian_score']
        scored_books.append(book)

    scored_books.sort(key=lambda x: x['final_score'], reverse=True)
    return scored_books[:10]
