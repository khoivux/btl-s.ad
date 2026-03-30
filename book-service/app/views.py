from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Book, Category
from .serializers import BookSerializer, CategorySerializer
from django.db.models import Q, F
import requests
import threading

from .utils import sync_book_to_catalog, delete_book_from_catalog

def _sync_category_rename(category_id, new_name):
    try:
        requests.put(f"http://catalog-service:8000/sync/category/{category_id}/", json={"category_name": new_name}, timeout=3)
    except Exception as e:
        print(f"[{__name__}] sync category error: {e}")


class CategoryListCreate(APIView):
    def get(self, request):
        categories = Category.objects.all()
        return Response(CategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class CategoryDetail(APIView):
    def get(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
            return Response(CategorySerializer(category).data)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=404)

    def put(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
            serializer = CategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                threading.Thread(target=_sync_category_rename, args=(category.id, category.name)).start()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=404)

    def delete(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
            category.delete()
            return Response(status=204)
        except Category.DoesNotExist:
            return Response({"error": "Category not found"}, status=404)

class BookListCreate(APIView):
    def get(self, request):
        queryset = Book.objects.all()
        
        search_query = request.query_params.get('q') or request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(author__icontains=search_query)
            )
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass     
                
        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        sort_by = request.query_params.get('sort')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        else:
            queryset = queryset.order_by('-id')

        serializer = BookSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class BookDetail(APIView):
    def get(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
            serializer = BookSerializer(book)
            return Response(serializer.data)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=404)

    def put(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
            serializer = BookSerializer(book, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=404)

    def delete(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
            book.delete()
            # Auto-sync is now handled by model save/delete!
            return Response(status=204)

        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=404)

class BookInventoryUpdate(APIView):
    """
    POST /books/<pk>/inventory/
    Body: {"change": -2} -> Decrement by 2
    """
    def post(self, request, pk):
        try:
            change = int(request.data.get('change', 0))
            book = Book.objects.get(pk=pk)
            book.stock += change
            book.save()  # Triggers sync via models.py save() hook
            serialized = BookSerializer(book).data
            return Response(serialized)

        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)