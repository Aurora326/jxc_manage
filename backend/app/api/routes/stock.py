from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models import StockBalance, StockLedger, Product
from app.schemas.schemas import StockBalanceOut, StockLedgerOut

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/balances", response_model=List[StockBalanceOut])
def list_balances(
    warehouse_id: Optional[int] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    stmt = select(StockBalance)
    if warehouse_id:
        stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.join(Product, Product.id == StockBalance.product_id).where(
            (Product.sku.like(like)) | (Product.name.like(like)) | (Product.model.like(like))
        )
    return list(db.execute(stmt).scalars().all())


@router.get("/ledger", response_model=List[StockLedgerOut])
def list_ledger(
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    stmt = select(StockLedger)
    if warehouse_id:
        stmt = stmt.where(StockLedger.warehouse_id == warehouse_id)
    if product_id:
        stmt = stmt.where(StockLedger.product_id == product_id)
    return list(db.execute(stmt).scalars().all())
