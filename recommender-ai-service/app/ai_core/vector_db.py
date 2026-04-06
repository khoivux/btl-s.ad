import os
import chromadb
from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import time

# Standardized on the very latest confirmed name: 'models/gemini-embedding-001'
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.GOOGLE_API_KEY
)

CHROMA_DATA_PATH = "/var/lib/chroma_db"
if not os.path.exists(CHROMA_DATA_PATH):
    os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

class VectorDBManger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDBManger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        self.collection = self.client.get_or_create_collection(
            name="bookstore_kb"
        )
        self._initialized = True

    def upsert_books(self, ids, documents, metadatas):
        # Generate embeddings batch by batch using the precisely verified name
        vectors = embeddings_model.embed_documents(documents)
        
        self.collection.upsert(
            ids=[str(i) for i in ids],
            documents=documents,
            metadatas=metadatas,
            embeddings=vectors
        )

    def query(self, query_text, n_results=5, where=None):
        # Query embedding using the same precise model name
        query_vector = embeddings_model.embed_query(query_text)
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            where=where
        )
        return results

    def clear_all(self):
        try:
            self.client.delete_collection(name="bookstore_kb")
        except:
            pass # Collection might not exist
        self.collection = self.client.get_or_create_collection(
            name="bookstore_kb"
        )

# Singleton access
vector_db = VectorDBManger()
