from django.db import models

class CategoryModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'catalog_category'

    def __str__(self):
        return self.name
