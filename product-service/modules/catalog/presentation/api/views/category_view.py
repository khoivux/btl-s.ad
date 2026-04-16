from rest_framework.views import APIView
from rest_framework.response import Response
from ....infrastructure.models.category_model import CategoryModel
from ....infrastructure.models.product_model import ProductModel


class CategoryListCreateAPI(APIView):
    def get(self, request):
        cats = CategoryModel.objects.all().values('id', 'name', 'description')
        return Response(list(cats))

    def post(self, request):
        name = request.data.get('name')
        desc = request.data.get('description', '')
        if not name:
            return Response({'error': 'name required'}, status=400)
        cat = CategoryModel.objects.create(name=name, description=desc)
        return Response({'id': cat.id, 'name': cat.name, 'description': cat.description}, status=201)


class CategoryDetailAPI(APIView):
    def put(self, request, pk):
        try:
            cat = CategoryModel.objects.get(pk=pk)
            cat.name = request.data.get('name', cat.name)
            cat.description = request.data.get('description', cat.description)
            cat.save()
            return Response({'id': cat.id, 'name': cat.name, 'description': cat.description})
        except CategoryModel.DoesNotExist:
            return Response({'error': 'Category not found'}, status=404)

    def delete(self, request, pk):
        try:
            CategoryModel.objects.get(pk=pk).delete()
            return Response(status=204)
        except CategoryModel.DoesNotExist:
            return Response({'error': 'Category not found'}, status=404)
