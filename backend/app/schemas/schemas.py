from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class WarehouseBase(BaseModel):
    code: Optional[str] = None
    name: str
    location: Optional[str] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseOut(WarehouseBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PartnerBase(BaseModel):
    type: str
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None


class PartnerCreate(PartnerBase):
    pass


class PartnerOut(PartnerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    sku: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    track_sn: bool = False
    warranty_months: Optional[int] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DocLineBase(BaseModel):
    line_no: int
    product_id: int
    qty: float = Field(gt=0)
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    from_wh_id: Optional[int] = None
    to_wh_id: Optional[int] = None
    remark: Optional[str] = None


class DocLineCreate(DocLineBase):
    pass


class DocLineOut(DocLineBase):
    id: int
    doc_id: int
    model_config = ConfigDict(from_attributes=True)


class DocBase(BaseModel):
    doc_type: str
    doc_no: str
    biz_date: date
    partner_id: Optional[int] = None
    from_wh_id: Optional[int] = None
    to_wh_id: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class DocCreate(DocBase):
    lines: List[DocLineCreate]


class DocOut(DocBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    posted_by: Optional[int] = None
    posted_at: Optional[datetime] = None
    lines: List[DocLineOut] = []

    model_config = ConfigDict(from_attributes=True)


class SNOut(BaseModel):
    id: int
    product_id: int
    sn: str
    status: str
    warehouse_id: Optional[int] = None
    in_doc_id: Optional[int] = None
    in_line_id: Optional[int] = None
    in_date: Optional[date] = None
    out_doc_id: Optional[int] = None
    out_line_id: Optional[int] = None
    out_date: Optional[date] = None
    warranty_start: Optional[date] = None
    warranty_end: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class StockBalanceOut(BaseModel):
    warehouse_id: int
    product_id: int
    qty_on_hand: float

    model_config = ConfigDict(from_attributes=True)


class StockLedgerOut(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    ref_doc_id: int
    ref_line_id: int
    ref_type: str
    biz_date: date
    in_qty: float
    out_qty: float
    unit_cost: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str
