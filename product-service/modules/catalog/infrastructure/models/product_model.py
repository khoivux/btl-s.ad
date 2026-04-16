from django.db import models
from .category_model import CategoryModel

class ProductModel(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    category = models.ForeignKey(CategoryModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'catalog_product'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 2. Trigger auto-sync to Catalog Mongo (assuming the same utility is accessible)
        self._sync_to_mongo()

    def delete(self, *args, **kwargs):
        product_id = self.id
        super().delete(*args, **kwargs)
        self._delete_from_mongo(product_id)

    def _sync_to_mongo(self):
        try:
            import requests
            data = {
                "sql_book_id": self.id,
                "name": self.name,
                "description": self.description,
                "category_id": self.category_id,
                "category_name": self.category.name if self.category else "Unknown",
                "price": float(self.price),
                "stock": self.stock,
                "image_url": self.image_url,
                "attributes": self.attributes
            }
            requests.post("http://catalog-service:8000/sync/product/", json=data, timeout=3)
        except Exception as e:
            print(f"[Sync] Failed to sync Product {self.id}: {e}")

    def _delete_from_mongo(self, product_id):
        try:
            import requests
            requests.delete(f"http://catalog-service:8000/sync/product/{product_id}/", timeout=3)
        except Exception as e:
            pass

    def __str__(self):
        return self.name
