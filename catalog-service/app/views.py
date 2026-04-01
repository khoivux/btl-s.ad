from rest_framework.views import APIView
from rest_framework.response import Response
from pymongo import MongoClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017/")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['bookstore']
books_collection = db['books']

try:
    books_collection.create_index([
        ("title", "text"), 
        ("author", "text"), 
        ("description", "text"), 
        ("isbn", "text")
    ], weights={
        "title": 10,
        "author": 5,
        "description": 1,
        "isbn": 10
    })
except Exception as e:
    print(f"MongoDB index setup error: {e}")


class CatalogSyncView(APIView):
    def post(self, request):
        book_data = request.data
        if 'id' not in book_data:
            return Response({'error': 'id required'}, status=400)
            
        book_id = book_data['id']
        book_data['_id'] = book_id
        if 'id' in book_data:
            del book_data['id']
            
        # Using replace_one ensures we remove any old problematic fields (like 'language')
        # that could conflict with MongoDB text indexes.
        books_collection.replace_one(
            {'_id': book_id},
            book_data,
            upsert=True
        )

        return Response({'status': 'synced', 'book_id': book_id})

class CatalogDeleteSyncView(APIView):
    def delete(self, request, book_id):
        books_collection.delete_one({'_id': book_id})
        return Response({'status': 'deleted', 'book_id': book_id})

class CatalogListView(APIView):
    def get(self, request):
        query = {}
        
        q = request.query_params.get('q')
        if q:
            query['$text'] = {'$search': q}
            
        cat_id = request.query_params.get('category_id')
        if cat_id:
            val = int(cat_id)
            query['$or'] = [
                {'category_id': val},
                {'category': val}
            ]

            
        lang_id = request.query_params.get('language_id')
        if lang_id:
            query['language_id'] = int(lang_id)
            
        format_id = request.query_params.get('format_id')
        if format_id:
            query['format_id'] = int(format_id)

        pub_id = request.query_params.get('publisher_id')
        if pub_id:
            query['publisher_id'] = int(pub_id)
            
        min_p = request.query_params.get('min_price')

        if min_p:
            query['price'] = query.get('price', {})
            query['price']['$gte'] = float(min_p)
            
        max_p = request.query_params.get('max_price')
        if max_p:
            query['price'] = query.get('price', {})
            query['price']['$lte'] = float(max_p)
            
        sort_by = request.query_params.get('sort_by', '_id')
        order = request.query_params.get('order', 'asc')
        sort_dir = 1 if order == 'asc' else -1

        cursor = books_collection.find(query)
        
        # Pagination
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        limit = int(request.query_params.get('limit', page_size))
        offset = int(request.query_params.get('offset', (page - 1) * limit))
        
        cursor = cursor.skip(offset).limit(limit)

        results = []
        for doc in cursor:
            doc['id'] = doc.pop('_id')
            doc['avg_rating'] = doc.get('avg_rating', 0)
            doc['total_reviews'] = doc.get('total_reviews', 0)
            results.append(doc)

        return Response({
            'total': books_collection.count_documents(query),
            'results': results
        })

class CatalogDetailView(APIView):
    def get(self, request, book_id):
        doc = books_collection.find_one({'_id': book_id})
        if not doc:
            return Response({'error': 'Not found'}, status=404)
        doc['id'] = doc.pop('_id')
        
        doc['avg_rating'] = doc.get('avg_rating', 0)
        doc['total_reviews'] = doc.get('total_reviews', 0)
        
        return Response(doc)

class CatalogCategorySyncView(APIView):
    def put(self, request, category_id):
        new_name = request.data.get('category_name')
        if not new_name:
             return Response({'error': 'category_name required'}, status=400)
             
        # Bulk update embedded category_name in all books having this category_id
        result = books_collection.update_many(
            {'category': category_id},
            {'$set': {'category_name': new_name}}
        )
        return Response({'status': 'updated', 'matched_count': result.matched_count})
