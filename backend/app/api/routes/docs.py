from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.deps import db_transaction, get_db
from app.models import Doc, DocLine
from app.schemas.schemas import DocCreate, DocOut
from app.services.post_doc import post_doc, PostError

router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.get("", response_model=List[DocOut])
def list_docs(
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    stmt = select(Doc)
    if doc_type:
        stmt = stmt.where(Doc.doc_type == doc_type)
    if status:
        stmt = stmt.where(Doc.status == status)
    if q:
        stmt = stmt.where(Doc.doc_no.like(f"%{q}%"))
    return list(db.execute(stmt).scalars().all())


@router.get("/{doc_id}", response_model=DocOut)
def get_doc(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Doc, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Doc not found")
    return doc


@router.post("", response_model=DocOut)
def create_doc(data: DocCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    with db_transaction(db):
        doc = Doc(
            doc_type=data.doc_type,
            doc_no=data.doc_no,
            biz_date=data.biz_date,
            partner_id=data.partner_id,
            from_wh_id=data.from_wh_id,
            to_wh_id=data.to_wh_id,
            status="DRAFT",
            remark=data.remark,
            created_by=user.id,
            created_at=datetime.utcnow(),
        )
        db.add(doc)
        db.flush()
        for line in data.lines:
            doc_line = DocLine(
                doc_id=doc.id,
                line_no=line.line_no,
                product_id=line.product_id,
                qty=line.qty,
                unit_price=line.unit_price,
                amount=line.amount,
                from_wh_id=line.from_wh_id,
                to_wh_id=line.to_wh_id,
                remark=line.remark,
            )
            db.add(doc_line)
        db.flush()
        return doc


@router.put("/{doc_id}", response_model=DocOut)
def update_doc(doc_id: int, data: DocCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Doc, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Doc not found")
    if doc.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Only DRAFT can be updated")

    with db_transaction(db):
        doc.doc_type = data.doc_type
        doc.doc_no = data.doc_no
        doc.biz_date = data.biz_date
        doc.partner_id = data.partner_id
        doc.from_wh_id = data.from_wh_id
        doc.to_wh_id = data.to_wh_id
        doc.remark = data.remark

        db.execute(delete(DocLine).where(DocLine.doc_id == doc_id))
        for line in data.lines:
            doc_line = DocLine(
                doc_id=doc.id,
                line_no=line.line_no,
                product_id=line.product_id,
                qty=line.qty,
                unit_price=line.unit_price,
                amount=line.amount,
                from_wh_id=line.from_wh_id,
                to_wh_id=line.to_wh_id,
                remark=line.remark,
            )
            db.add(doc_line)
        return doc


@router.post("/{doc_id}/approve", response_model=DocOut)
def approve_doc(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Doc, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Doc not found")
    if doc.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Only DRAFT can be approved")
    doc.status = "APPROVED"
    doc.approved_by = user.id
    doc.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/{doc_id}/post", response_model=DocOut)
def post_doc_endpoint(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        with db_transaction(db):
            doc = post_doc(db, doc_id, user.id)
        db.refresh(doc)
        return doc
    except PostError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
