from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from django.db.models import Avg, Count

class ReviewListCreate(APIView):
    """
    GET /reviews/<book_id>/ → Returns all reviews for a book, plus avg rating & count.
    POST /reviews/ → Create or Update a review. (Upsert).
    """
    def get(self, request, book_id):
        reviews = Review.objects.filter(book_id=book_id).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        
        stats = Review.objects.filter(book_id=book_id).aggregate(
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
        book_id = request.data.get('book_id')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        customer_name = request.data.get('customer_name', 'User')

        if not customer_id or not book_id or not rating:
            return Response({'error': 'customer_id, book_id and rating are required'}, status=400)

        # Upsert
        review, created = Review.objects.update_or_create(
            customer_id=customer_id,
            book_id=book_id,
            defaults={'rating': rating, 'comment': comment, 'customer_name': customer_name}
        )
        
        return Response(ReviewSerializer(review).data, status=201 if created else 200)
