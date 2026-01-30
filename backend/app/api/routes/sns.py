from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import db_transaction, get_db
from app.models import DocLine, Product, ProductSN, DocLineSN
from app.schemas.schemas import SNOut

router = APIRouter(prefix="/api", tags=["sns"])


@router.get("/sns", response_model=List[SNOut])
def list_sns(
    sn: Optional[str] = None,
    status: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    stmt = select(ProductSN)
    if sn:
        stmt = stmt.where(ProductSN.sn == sn)
    if status:
        stmt = stmt.where(ProductSN.status == status)
    if warehouse_id:
        stmt = stmt.where(ProductSN.warehouse_id == warehouse_id)
    if product_id:
        stmt = stmt.where(ProductSN.product_id == product_id)
    return list(db.execute(stmt).scalars().all())


@router.post("/docs/{doc_id}/lines/{line_id}/sns/import", response_model=List[SNOut])
def import_sns(doc_id: int, line_id: int, body: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    sns = body.get("sns") or []
    if not isinstance(sns, list) or not sns:
        raise HTTPException(status_code=400, detail="sns required")

    line = db.get(DocLine, line_id)
    if line is None or line.doc_id != doc_id:
        raise HTTPException(status_code=404, detail="Line not found")

    product = db.get(Product, line.product_id)
    if product is None or not product.track_sn:
        raise HTTPException(status_code=400, detail="Product does not track SN")

    created = []
    with db_transaction(db):
        for sn_code in sns:
            existing = db.execute(select(ProductSN).where(ProductSN.sn == sn_code)).scalar_one_or_none()
            if existing:
                if existing.product_id != product.id:
                    raise HTTPException(status_code=400, detail="SN product mismatch")
                if existing.status not in ("LOCKED", "IN_STOCK"):
                    raise HTTPException(status_code=400, detail="SN status invalid")
                sn_obj = existing
            else:
                sn_obj = ProductSN(product_id=product.id, sn=sn_code, status="LOCKED")
                db.add(sn_obj)
                db.flush()
            link = db.execute(
                select(DocLineSN).where(DocLineSN.line_id == line_id, DocLineSN.sn_id == sn_obj.id)
            ).scalar_one_or_none()
            if link is None:
                db.add(DocLineSN(doc_id=doc_id, line_id=line_id, sn_id=sn_obj.id))
            created.append(sn_obj)
    return created


@router.post("/docs/{doc_id}/lines/{line_id}/sns/scan", response_model=SNOut)
def scan_sn(doc_id: int, line_id: int, body: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    sn_code = body.get("sn")
    if not sn_code:
        raise HTTPException(status_code=400, detail="sn required")

    result = import_sns(doc_id, line_id, {"sns": [sn_code]}, db, user)
    return result[0]


@router.delete("/docs/{doc_id}/lines/{line_id}/sns/{sn_id}")
def delete_sn_link(
    doc_id: int,
    line_id: int,
    sn_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    link = db.execute(
        select(DocLineSN).where(
            DocLineSN.doc_id == doc_id,
            DocLineSN.line_id == line_id,
            DocLineSN.sn_id == sn_id,
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="SN link not found")
    with db_transaction(db):
        db.delete(link)
    return {"ok": True}
