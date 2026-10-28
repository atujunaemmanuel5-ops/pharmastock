
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ExpiryStatus(str,Enum):
    # Defines the permitted expiry statuses.
    EXPIRED= "Expired"
    IS_EXPIRING_SOON="Expiring soon"
    

class ExpiryRecord(BaseModel):
    # Defines the structure of an expiry record
    batch_no:str
    batch_id: str
    drug_id: str
    qty_on_hand: int
    expiry_date:datetime
    received_date:datetime
    lead_time_days: int
    pack_size:int
    as_of_date:datetime
    is_simulated:bool
    days_to_expiry:int
    expiry_status:ExpiryStatus

class StockSummaryRecord(BaseModel):
    # Defines structure of the stock summary record
    drug_id:str
    total_stock:int




