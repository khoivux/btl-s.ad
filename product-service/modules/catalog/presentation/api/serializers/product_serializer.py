from rest_framework import serializers

class ProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    price = serializers.FloatField()
    stock = serializers.IntegerField()
    image_url = serializers.URLField(allow_blank=True)
    category_id = serializers.IntegerField(allow_null=True, required=False)
    attributes = serializers.JSONField()
