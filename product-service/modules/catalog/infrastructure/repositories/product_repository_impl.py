from ..models.product_model import ProductModel
from ...domain.entities.product import ProductEntity

class ProductRepositoryImpl:
    def get_all(self):
        return ProductModel.objects.all()

    def get_by_id(self, product_id: int):
        try:
            model = ProductModel.objects.get(pk=product_id)
            return self._to_entity(model)
        except ProductModel.DoesNotExist:
            return None

    def save(self, entity: ProductEntity):
        model, created = ProductModel.objects.update_or_create(
            id=entity.id,
            defaults={
                'name': entity.name,
                'description': entity.description,
                'price': entity.price,
                'stock': entity.stock,
                'image_url': entity.image_url,
                'category_id': entity.category_id,
                'attributes': entity.attributes
            }
        )
        return self._to_entity(model)

    def delete(self, product_id: int):
        ProductModel.objects.filter(pk=product_id).delete()

    def _to_entity(self, model: ProductModel) -> ProductEntity:
        return ProductEntity(
            id=model.id,
            name=model.name,
            description=model.description,
            price=float(model.price),
            stock=model.stock,
            image_url=model.image_url,
            category_id=model.category_id,
            attributes=model.attributes
        )
