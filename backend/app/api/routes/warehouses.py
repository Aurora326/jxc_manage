from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models import Warehouse
from app.schemas.schemas import WarehouseCreate, WarehouseOut

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


@router.get("", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list(db.execute(select(Warehouse)).scalars().all())


@router.post("", response_model=WarehouseOut)
def create_warehouse(data: WarehouseCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    wh = Warehouse(**data.model_dump())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh
