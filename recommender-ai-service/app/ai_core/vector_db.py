import os
import chromadb
from django.conf import settings
import google.generativeai as genai

# Configure Google Generative AI
if hasattr(settings, 'GOOGLE_API_KEY'):
    genai.configure(api_key=settings.GOOGLE_API_KEY)

CHROMA_DATA_PATH = os.path.join(settings.BASE_DIR, "chroma_db")
if not os.path.exists(CHROMA_DATA_PATH):
    os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

class VectorDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        self.collection = self.client.get_or_create_collection(
            name="microstore_kb"
        )
        self._initialized = True

    def clear_all(self):
        """Wipes the current collection to start fresh."""
        try:
            self.client.delete_collection("microstore_kb")
            self.collection = self.client.get_or_create_collection("microstore_kb")
        except:
            pass

    def get_embeddings(self, texts, task_type="retrieval_document"):
        """Helper to get embeddings using Google text-embedding-004."""
        # result['embedding'] will be a list of lists if texts is a list
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=texts,
            task_type=task_type
        )
        return result['embedding']

    def upsert_products(self, ids, documents, metadatas):
        """Renamed from upsert_books to upsert_products for clarity."""
        # 1. Generate embeddings manually using Google AI
        embeddings = self.get_embeddings(documents)
        
        # 2. Upsert to collection
        self.collection.upsert(
            ids=[str(i) for i in ids],
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
    
    # Backwards compatibility alias
    def upsert_books(self, ids, documents, metadatas):
        self.upsert_products(ids, documents, metadatas)

    def query(self, query_text, n_results=5, where=None):
        # 1. Generate embedding for query
        query_embedding = self.get_embeddings(query_text, task_type="retrieval_query")
        
        # 2. Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        return results

# Singleton access
vector_db = VectorDBManager()
