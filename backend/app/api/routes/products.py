from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models import Product
from app.schemas.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=List[ProductOut])
def list_products(q: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(Product)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Product.sku.like(like)) | (Product.name.like(like)) | (Product.model.like(like))
        )
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product
