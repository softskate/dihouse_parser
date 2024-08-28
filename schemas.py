from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    brandName: Optional[str] = None
    sku: str
    productId: str
    ean: Optional[str] = None
    name: str
    qty: str
    price: int
    priceRRC: Optional[int] = None
    category: str

