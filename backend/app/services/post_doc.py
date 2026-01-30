from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Doc, DocLine, Product, StockBalance, StockLedger, ProductSN, DocLineSN


class PostError(Exception):
    pass


def _get_balance(db: Session, wh_id: int, product_id: int):
    stmt = select(StockBalance).where(
        StockBalance.warehouse_id == wh_id,
        StockBalance.product_id == product_id,
    )
    balance = db.execute(stmt).scalar_one_or_none()
    return balance.qty_on_hand if balance else 0


def _inc_balance(db: Session, wh_id: int, product_id: int, qty):
    stmt = select(StockBalance).where(
        StockBalance.warehouse_id == wh_id,
        StockBalance.product_id == product_id,
    )
    balance = db.execute(stmt).scalar_one_or_none()
    if balance is None:
        balance = StockBalance(warehouse_id=wh_id, product_id=product_id, qty_on_hand=0)
        db.add(balance)
    balance.qty_on_hand = balance.qty_on_hand + qty


def _dec_balance(db: Session, wh_id: int, product_id: int, qty):
    _inc_balance(db, wh_id, product_id, -qty)


def _add_ledger(db: Session, wh_id: int, line: DocLine, doc: Doc, in_qty, out_qty):
    ledger = StockLedger(
        warehouse_id=wh_id,
        product_id=line.product_id,
        ref_doc_id=doc.id,
        ref_line_id=line.id,
        ref_type=doc.doc_type,
        biz_date=doc.biz_date,
        in_qty=in_qty,
        out_qty=out_qty,
    )
    db.add(ledger)


def _load_line_sns(db: Session, line_id: int):
    stmt = select(ProductSN).join(DocLineSN, DocLineSN.sn_id == ProductSN.id).where(
        DocLineSN.line_id == line_id
    )
    return list(db.execute(stmt).scalars().all())


def _ensure_sn_count(line: DocLine, sns: Iterable[ProductSN]):
    if len(list(sns)) != int(line.qty):
        raise PostError("SN count must equal qty")


def post_doc(db: Session, doc_id: int, user_id: int):
    doc = db.get(Doc, doc_id)
    if doc is None:
        raise PostError("doc not found")

    if doc.status == "POSTED":
        return doc

    if doc.status not in ("APPROVED", "DRAFT"):
        raise PostError("doc status not allowed")

    lines = db.execute(select(DocLine).where(DocLine.doc_id == doc_id)).scalars().all()

    # 1) validations
    for line in lines:
        product = db.get(Product, line.product_id)
        if product is None:
            raise PostError("product not found")

        if doc.doc_type == "PURCHASE_IN":
            wh = line.to_wh_id or doc.to_wh_id
            if not wh:
                raise PostError("to_wh_id required")
            if product.track_sn:
                sns = _load_line_sns(db, line.id)
                _ensure_sn_count(line, sns)
                for sn in sns:
                    if sn.status not in ("LOCKED", "IN_STOCK"):
                        raise PostError("sn status invalid")

        if doc.doc_type == "SALES_OUT":
            wh = line.from_wh_id or doc.from_wh_id
            if not wh:
                raise PostError("from_wh_id required")
            if _get_balance(db, wh, line.product_id) < line.qty:
                raise PostError("insufficient stock")
            if product.track_sn:
                sns = _load_line_sns(db, line.id)
                _ensure_sn_count(line, sns)
                for sn in sns:
                    if sn.status != "IN_STOCK" or sn.warehouse_id != wh:
                        raise PostError("sn not in stock")

        if doc.doc_type == "TRANSFER":
            from_wh = line.from_wh_id or doc.from_wh_id
            to_wh = line.to_wh_id or doc.to_wh_id
            if not from_wh or not to_wh or from_wh == to_wh:
                raise PostError("invalid transfer warehouses")
            if _get_balance(db, from_wh, line.product_id) < line.qty:
                raise PostError("insufficient stock")
            if product.track_sn:
                sns = _load_line_sns(db, line.id)
                _ensure_sn_count(line, sns)
                for sn in sns:
                    if sn.status != "IN_STOCK" or sn.warehouse_id != from_wh:
                        raise PostError("sn not in stock")

    # 2) apply
    for line in lines:
        product = db.get(Product, line.product_id)

        if doc.doc_type == "PURCHASE_IN":
            wh = line.to_wh_id or doc.to_wh_id
            _add_ledger(db, wh, line, doc, in_qty=line.qty, out_qty=0)
            _inc_balance(db, wh, line.product_id, line.qty)
            if product.track_sn:
                for sn in _load_line_sns(db, line.id):
                    sn.status = "IN_STOCK"
                    sn.warehouse_id = wh
                    sn.in_doc_id = doc.id
                    sn.in_line_id = line.id
                    sn.in_date = doc.biz_date

        elif doc.doc_type == "SALES_OUT":
            wh = line.from_wh_id or doc.from_wh_id
            _add_ledger(db, wh, line, doc, in_qty=0, out_qty=line.qty)
            _dec_balance(db, wh, line.product_id, line.qty)
            if product.track_sn:
                for sn in _load_line_sns(db, line.id):
                    sn.status = "OUT_STOCK"
                    sn.warehouse_id = wh
                    sn.out_doc_id = doc.id
                    sn.out_line_id = line.id
                    sn.out_date = doc.biz_date
                    sn.warranty_start = doc.biz_date
                    if product.warranty_months:
                        sn.warranty_end = doc.biz_date + timedelta(days=30 * product.warranty_months)

        elif doc.doc_type == "TRANSFER":
            from_wh = line.from_wh_id or doc.from_wh_id
            to_wh = line.to_wh_id or doc.to_wh_id
            _add_ledger(db, from_wh, line, doc, in_qty=0, out_qty=line.qty)
            _dec_balance(db, from_wh, line.product_id, line.qty)
            _add_ledger(db, to_wh, line, doc, in_qty=line.qty, out_qty=0)
            _inc_balance(db, to_wh, line.product_id, line.qty)
            if product.track_sn:
                for sn in _load_line_sns(db, line.id):
                    sn.status = "IN_STOCK"
                    sn.warehouse_id = to_wh

    doc.status = "POSTED"
    doc.posted_by = user_id
    doc.posted_at = datetime.utcnow()
    return doc
