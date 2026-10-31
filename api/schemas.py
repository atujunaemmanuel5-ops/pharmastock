from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ExpiryRecord(BaseModel):
    batch_no: str
    batch_id: str
    drug_id: str
    generic_name: str
    qty_on_hand: int
    expiry_date: datetime
    received_date: datetime
    lead_time_days: int
    pack_size: int
    as_of_date: datetime
    is_simulated: bool
    days_to_expiry: int
    expiry_status: str
    is_fefo_pick: bool
    units_at_risk: int = 0


class StockSummaryRecord(BaseModel):
    drug_id: str
    total_stock: int
    usable_stock: int


class DrugBank(BaseModel):
    drug_id: str
    generic_name: str
    strength: str | None = None
    form: str | None = None
    atc_code: str | None = None
    atc_level4: str | None = None
    is_simulated: bool = True


class ProductGroup(BaseModel):
    code: str
    description: str
    first_date: str
    last_date: str


class DispenseRequest(BaseModel):
    drug_ids: list[str] = Field(min_length=1)
    prescription_reference: str | None = None
    override_reason: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class ConfirmRequest(DispenseRequest):
    pass


class UploadSummary(BaseModel):
    rows: int
    groups: int
    first_date: str
    last_date: str
    message: str


class MedicationCreate(BaseModel):
    drug_id: str | None = None
    generic_name: str = Field(min_length=2, max_length=255)
    strength: str | None = None
    form: str | None = None
    atc_code: str | None = None
    atc_level4: str | None = None
    pack_size: int = Field(default=1, ge=1, le=100000)
    lead_time_days: int = Field(default=7, ge=0, le=365)
    initial_stock: int = Field(default=0, ge=0)
    expiry_date: date | None = None
    prescription_required: bool = False
    source_name: str | None = None
    source_ref: str | None = None


class GenericResponse(BaseModel):
    data: dict[str, Any]
