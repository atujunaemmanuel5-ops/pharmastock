from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ExpiryStatus(str, Enum):
    EXPIRED = "Expired"
    CRITICAL = "Critical"
    WATCH = "Watch"
    OK = "OK"


class ExpiryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    expiry_status: ExpiryStatus
    is_fefo_pick: bool


class StockSummaryRecord(BaseModel):
    drug_id: str
    total_stock: int
    usable_stock: int