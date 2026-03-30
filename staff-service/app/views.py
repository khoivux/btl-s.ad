from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

BOOK_SERVICE_URL = "http://book-service:8000"

@method_decorator(csrf_exempt, name='dispatch')
class StaffBookManager(APIView):
    def post(self, request):
        # Admin adding a new book
        # Staff check should ideally happen here or at API Gateway
        r = requests.post(f"{BOOK_SERVICE_URL}/books/", json=request.data)
        try:
            return Response(r.json(), status=r.status_code)
        except:
            return Response({"error": r.text}, status=r.status_code)

@method_decorator(csrf_exempt, name='dispatch')
class StaffBookDetailManager(APIView):
    def put(self, request, pk):
        r = requests.put(f"{BOOK_SERVICE_URL}/books/{pk}/", json=request.data)
        try:
            return Response(r.json(), status=r.status_code)
        except:
            return Response({"error": r.text}, status=r.status_code)

    def delete(self, request, pk):
        r = requests.delete(f"{BOOK_SERVICE_URL}/books/{pk}/")
        if r.status_code == 204:
            return Response({'status': 'deleted'})
        return Response({'error': 'Failed to delete'}, status=r.status_code)

@method_decorator(csrf_exempt, name='dispatch')
class StaffLogin(APIView):
    def post(self, request):
        from .models import Staff
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            staff = Staff.objects.get(username=username, password=password)
            return Response({'id': staff.id, 'username': staff.username, 'role': staff.role})
        except Staff.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)
