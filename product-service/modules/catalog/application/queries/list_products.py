from django.db.models import Q
from ...infrastructure.models.product_model import ProductModel
from ...infrastructure.repositories.product_repository_impl import ProductRepositoryImpl

class ListProductsQuery:
    def __init__(self, repository=None):
        self.repository = repository or ProductRepositoryImpl()

    def execute(self, filters, page=1, page_size=10):
        queryset = ProductModel.objects.all()
        
        search_query = filters.get('q') or filters.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )
        
        # We can also filter through JSONB fields
        category_id = filters.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        min_price = filters.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
            
        max_price = filters.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))

        sort_by = filters.get('sort')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        else:
            queryset = queryset.order_by('-id')

        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated_queryset = queryset[start:end]

        return {
            'results': [self.repository._to_entity(m) for m in paginated_queryset],
            'total': total_count,
            'page': page,
            'page_size': page_size
        }
