from rest_framework.views import APIView
from rest_framework.response import Response
from pymongo import MongoClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017/")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['bookstore']
products_collection = db['products']

# Setup text index on name + description for full-text search across all product types
try:
    products_collection.create_index([
        ("name", "text"),
        ("description", "text"),
    ], weights={
        "name": 10,
        "description": 3,
    })
except Exception as e:
    print(f"MongoDB index setup error: {e}")


# ─── Sync from product-service ───────────────────────────────────────────────

class ProductSyncView(APIView):
    """POST /sync/product/ — Upsert a product document from product-service."""
    def post(self, request):
        data = request.data
        product_id = data.get('sql_book_id') or data.get('id')
        if not product_id:
            return Response({'error': 'id required'}, status=400)

        doc = {
            '_id': product_id,
            'name': data.get('name') or data.get('title', ''),
            'description': data.get('description', ''),
            'price': data.get('price', 0),
            'stock': data.get('stock', 0),
            'image_url': data.get('image_url', ''),
            'category_id': data.get('category_id'),
            'category_name': data.get('category_name', ''),
            'attributes': data.get('attributes', {}),
        }

        products_collection.replace_one({'_id': product_id}, doc, upsert=True)
        return Response({'status': 'synced', 'product_id': product_id})


class ProductDeleteSyncView(APIView):
    """DELETE /sync/product/<product_id>/ — Remove a product document."""
    def delete(self, request, product_id):
        products_collection.delete_one({'_id': product_id})
        return Response({'status': 'deleted', 'product_id': product_id})


# Keep legacy book endpoints for backward compat (maps to same collection)
class CatalogSyncView(ProductSyncView):
    """POST /sync/book/ — Legacy alias for ProductSyncView."""
    pass

class CatalogDeleteSyncView(ProductDeleteSyncView):
    """DELETE /sync/book/<book_id>/ — Legacy alias."""
    def delete(self, request, book_id):
        return super().delete(request, book_id)


# ─── Category sync ────────────────────────────────────────────────────────────

class CatalogCategorySyncView(APIView):
    def put(self, request, category_id):
        new_name = request.data.get('category_name')
        if not new_name:
            return Response({'error': 'category_name required'}, status=400)
        result = products_collection.update_many(
            {'category_id': category_id},
            {'$set': {'category_name': new_name}}
        )
        return Response({'status': 'updated', 'matched_count': result.matched_count})


# ─── List / Search ────────────────────────────────────────────────────────────

class CatalogListView(APIView):
    def get(self, request):
        query = {}

        # Full-text search by product name / description (all types)
        q = request.query_params.get('q')
        if q:
            query['$text'] = {'$search': q}

        # Category filter
        cat_id = request.query_params.get('category_id')
        if cat_id:
            query['category_id'] = int(cat_id)

        # Price range
        min_p = request.query_params.get('min_price')
        if min_p:
            query['price'] = query.get('price', {})
            query['price']['$gte'] = float(min_p)

        max_p = request.query_params.get('max_price')
        if max_p:
            query['price'] = query.get('price', {})
            query['price']['$lte'] = float(max_p)

        # Sorting
        sort_by = request.query_params.get('sort', 'price_asc')
        sort_field = 'price' if 'price' in sort_by else '_id'
        sort_dir = -1 if 'desc' in sort_by else 1

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        offset = (page - 1) * page_size

        cursor = products_collection.find(query).sort(sort_field, sort_dir).skip(offset).limit(page_size)

        results = []
        for doc in cursor:
            doc['id'] = doc.pop('_id')
            doc.setdefault('avg_rating', 0)
            doc.setdefault('total_reviews', 0)
            results.append(doc)

        return Response({
            'total': products_collection.count_documents(query),
            'results': results,
            'page': page,
            'page_size': page_size,
        })


class CatalogDetailView(APIView):
    def get(self, request, book_id):
        doc = products_collection.find_one({'_id': book_id})
        if not doc:
            return Response({'error': 'Not found'}, status=404)
        doc['id'] = doc.pop('_id')
        doc.setdefault('avg_rating', 0)
        doc.setdefault('total_reviews', 0)
        return Response(doc)
