from ...domain.entities.product import ProductEntity
from ...infrastructure.repositories.product_repository_impl import ProductRepositoryImpl

class ProductService:
    def __init__(self, repository=None):
        self.repository = repository or ProductRepositoryImpl()

    def create_product(self, data: dict) -> ProductEntity:
        entity = ProductEntity(
            name=data.get('name', ''),
            description=data.get('description', ''),
            price=float(data.get('price', 0.0)),
            stock=int(data.get('stock', 0)),
            image_url=data.get('image_url', ''),
            category_id=data.get('category_id'),
            attributes=data.get('attributes', {})
        )
        entity.validate()
        return self.repository.save(entity)

    def update_inventory(self, product_id: int, change: int):
        entity = self.repository.get_by_id(product_id)
        if not entity:
            raise ValueError("Product not found")
        
        entity.stock += change
        entity.validate() # will throw if stock < 0
        return self.repository.save(entity)
