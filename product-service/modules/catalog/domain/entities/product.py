from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ProductEntity:
    name: str
    description: str
    category_id: int
    price: float
    image_url: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    stock: int = 0

    def validate(self):
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")
        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")
