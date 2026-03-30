import os
import requests
from pymongo import MongoClient

def sync_all():
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017/")
    client = MongoClient(MONGO_URL)
    db = client['bookstore']
    books_collection = db['books']
    
    # Try fetch books locally via service network if running in docker
    book_service_url = os.environ.get("BOOK_SERVICE_URL", "http://book-service:8000")
    print(f"Fetching books from: {book_service_url}/books/")
    
    try:
        r = requests.get(f"{book_service_url}/books/", timeout=10)
        books = r.json()
        
        count = 0
        for book in books:
            book_id = book.get('id')
            if not book_id:
                continue
                
            # Remove fields that conflict with MongoDB reserved fields
            if 'language' in book:
                del book['language']
                
            book['_id'] = book_id
            if 'id' in book:
                del book['id']
            
            books_collection.replace_one({'_id': book_id}, book, upsert=True)
            count += 1
            
        print(f"Synced {count} books from book-service to MongoDB.")
        
        # Ensure indices
        books_collection.create_index([("title", "text"), ("author", "text")])
        print("Text index created successfully.")
    except Exception as e:
        print(f"Error syncing books: {e}")

if __name__ == "__main__":
    sync_all()
