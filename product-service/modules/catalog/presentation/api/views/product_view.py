from rest_framework.views import APIView
from rest_framework.response import Response
from ....application.services.product_service import ProductService
from ....application.queries.list_products import ListProductsQuery
from ....infrastructure.repositories.product_repository_impl import ProductRepositoryImpl
from ..serializers.product_serializer import ProductSerializer
from dataclasses import asdict

class ProductListCreateAPI(APIView):
    def get(self, request):
        query_service = ListProductsQuery()
        result = query_service.execute(
            filters=request.query_params,
            page=int(request.query_params.get('page', 1)),
            page_size=int(request.query_params.get('page_size', 10))
        )
        
        # Serialize entities to dicts
        result['results'] = [asdict(entity) for entity in result['results']]
        return Response(result)

    def post(self, request):
        service = ProductService()
        try:
            entity = service.create_product(request.data)
            return Response(asdict(entity), status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class ProductDetailAPI(APIView):
    def get(self, request, pk):
        repo = ProductRepositoryImpl()
        entity = repo.get_by_id(pk)
        if not entity:
            return Response({"error": "Product not found"}, status=404)
        return Response(asdict(entity))

    def delete(self, request, pk):
        repo = ProductRepositoryImpl()
        entity = repo.get_by_id(pk)
        if not entity:
            return Response({"error": "Product not found"}, status=404)
        repo.delete(pk)
        return Response(status=204)

class ProductInventoryAPI(APIView):
    def post(self, request, pk):
        service = ProductService()
        change = int(request.data.get('change', 0))
        try:
            entity = service.update_inventory(pk, change)
            return Response(asdict(entity))
        except Exception as e:
            return Response({"error": str(e)}, status=400)
