import pymongo
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

client = pymongo.MongoClient(settings.MONGO_URL)
db = client['interaction_db']
logs_collection = db['logs']

class LogInteraction(APIView):
    def post(self, request):
        """
        Expects:
        {
            "user_id": 1,
            "action": "view_product", # viewed, searched, bought
            "target_id": "product123" # or keyword
        }
        """
        data = request.data
        if not data.get('user_id') or not data.get('action') or not data.get('target_id'):
            return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)
        
        log_doc = {
            "user_id": int(data['user_id']),
            "action": data['action'],
            "target_id": str(data['target_id']),
            "timestamp": datetime.utcnow()
        }
        logs_collection.insert_one(log_doc)
        return Response({"status": "logged"}, status=status.HTTP_201_CREATED)


class GetUserLogs(APIView):
    def get(self, request, user_id):
        logs = list(logs_collection.find({"user_id": user_id}).sort("timestamp", -1))
        for log in logs:
            log['_id'] = str(log['_id'])
        return Response(logs)
