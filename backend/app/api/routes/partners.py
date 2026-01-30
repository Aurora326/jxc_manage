from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models import Partner
from app.schemas.schemas import PartnerCreate, PartnerOut

router = APIRouter(prefix="/api/partners", tags=["partners"])


@router.get("", response_model=List[PartnerOut])
def list_partners(type: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(Partner)
    if type:
        stmt = stmt.where(Partner.type == type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Partner.name.like(like))
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=PartnerOut)
def create_partner(data: PartnerCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    partner = Partner(**data.model_dump())
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.put("/{partner_id}", response_model=PartnerOut)
def update_partner(partner_id: int, data: PartnerCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    for key, value in data.model_dump().items():
        setattr(partner, key, value)
    db.commit()
    db.refresh(partner)
    return partner
