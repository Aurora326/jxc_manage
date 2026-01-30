from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[Optional[str]] = mapped_column(String(200))


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(String(200))


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100))
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    track_sn: Mapped[bool] = mapped_column(Boolean, default=False)
    warranty_months: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Doc(Base):
    __tablename__ = "docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(30), index=True)
    doc_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    biz_date: Mapped[date] = mapped_column(Date, index=True)

    partner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("partners.id"))
    from_wh_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))
    to_wh_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))

    status: Mapped[str] = mapped_column(String(20), index=True, default="DRAFT")
    remark: Mapped[Optional[str]] = mapped_column(String(500))

    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    posted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    lines: Mapped[list["DocLine"]] = relationship(back_populates="doc", cascade="all, delete-orphan")


class DocLine(Base):
    __tablename__ = "doc_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("docs.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    qty: Mapped[Numeric] = mapped_column(Numeric(18, 2))
    unit_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(18, 2))
    amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(18, 2))

    from_wh_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), index=True)
    to_wh_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), index=True)

    remark: Mapped[Optional[str]] = mapped_column(String(500))

    doc: Mapped[Doc] = relationship(back_populates="lines")

    __table_args__ = (
        UniqueConstraint("doc_id", "line_no", name="uq_doc_line_no"),
        CheckConstraint("qty > 0", name="ck_doc_line_qty_gt_zero"),
    )


class StockBalance(Base):
    __tablename__ = "stock_balances"

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    qty_on_hand: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    ref_doc_id: Mapped[int] = mapped_column(ForeignKey("docs.id"))
    ref_line_id: Mapped[int] = mapped_column(ForeignKey("doc_lines.id"))
    ref_type: Mapped[str] = mapped_column(String(30))
    biz_date: Mapped[date] = mapped_column(Date)
    in_qty: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)
    out_qty: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)
    unit_cost: Mapped[Optional[Numeric]] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ledger_wh_prod_date", "warehouse_id", "product_id", "biz_date"),
        Index("ix_ledger_ref_doc", "ref_doc_id"),
    )


class ProductSN(Base):
    __tablename__ = "product_sns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sn: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), index=True)

    in_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("docs.id"))
    in_line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doc_lines.id"))
    in_date: Mapped[Optional[date]] = mapped_column(Date)

    out_doc_id: Mapped[Optional[int]] = mapped_column(ForeignKey("docs.id"))
    out_line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doc_lines.id"))
    out_date: Mapped[Optional[date]] = mapped_column(Date)

    warranty_start: Mapped[Optional[date]] = mapped_column(Date)
    warranty_end: Mapped[Optional[date]] = mapped_column(Date)


class DocLineSN(Base):
    __tablename__ = "doc_line_sns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("docs.id"), index=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("doc_lines.id"), index=True)
    sn_id: Mapped[int] = mapped_column(ForeignKey("product_sns.id"))

    __table_args__ = (
        UniqueConstraint("line_id", "sn_id", name="uq_line_sn"),
        Index("ix_doc_line_sn", "doc_id", "sn_id"),
    )
