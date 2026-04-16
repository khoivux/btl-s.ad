from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from django.db.models import Avg, Count

class ReviewListCreate(APIView):
    """
    GET /reviews/<product_id>/ → Returns all reviews for a product, plus avg rating & count.
    POST /reviews/ → Create or Update a review. (Upsert).
    """
    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        
        stats = Review.objects.filter(product_id=product_id).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        return Response({
            'avg_rating': round(stats['avg_rating'] or 0, 1),
            'total_reviews': stats['total_reviews'],
            'reviews': serializer.data
        })

    def post(self, request):
        customer_id = request.data.get('customer_id')
        product_id = request.data.get('product_id') or request.data.get('book_id') # handle both for transition
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        customer_name = request.data.get('customer_name', 'User')

        if not customer_id or not product_id or not rating:
            return Response({'error': 'customer_id, product_id and rating are required'}, status=400)

        # Upsert
        review, created = Review.objects.update_or_create(
            customer_id=customer_id,
            product_id=product_id,
            defaults={'rating': rating, 'comment': comment, 'customer_name': customer_name}
        )
        
        
        return Response(ReviewSerializer(review).data, status=201 if created else 200)

class ReviewReadAll(APIView):
    """
    GET /reviews/all/ → Get every single review for training.
    """
    def get(self, request):
        reviews = Review.objects.all().order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
