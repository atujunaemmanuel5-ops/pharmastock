from ast import List
import logging

from fastapi import FastAPI, HTTPException

from src.config import ATC_CODES

from api.schemas import DrugBank, ExpiryRecord, StockSummaryRecord
from src.inventory import (
    load_inventory_batches,
    load_drug_catalogue,
    add_drug_names,
    create_expiry_report,
    summarize_stock,
    
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PharmaStock AI API")


@app.get("/health")
def health_status():
    """Confirm that the API process is running."""

    return {"status": "ok"}


@app.get(
    "/inventory/expiry",
    response_model=list[ExpiryRecord],
)
def expiry_report():
    """Return inventory batches with expiry and FEFO information."""

    try:
        batches = load_inventory_batches()
        drugs = load_drug_catalogue()

        inventory = add_drug_names(batches, drugs)
        report = create_expiry_report(inventory)

        return report.to_dict(orient="records")

    except FileNotFoundError as exc:
        logger.exception("Required inventory data file was not found.")

        raise HTTPException(
            status_code=500,
            detail="Required inventory data is unavailable.",
        ) from exc

    except Exception as exc:
        logger.exception("Could not generate expiry report.")

        raise HTTPException(
            status_code=500,
            detail="Could not generate expiry report.",
        ) from exc


@app.get(
    "/inventory/stock-summary",
    response_model=list[StockSummaryRecord],
)
def stock_summary():
    """Return physical and usable stock quantities by drug."""

    try:
        batches = load_inventory_batches()
        stock = summarize_stock(batches)

        return stock.to_dict(orient="records")

    except FileNotFoundError as exc:
        logger.exception("Required inventory data file was not found.")

        raise HTTPException(
            status_code=500,
            detail="Required inventory data is unavailable.",
        ) from exc

    except Exception as exc:
        logger.exception("Could not generate stock summary.")

        raise HTTPException(
            status_code=500,
            detail="Could not generate stock summary.",
        ) from exc

# drug end point

@app.get("/inventory/drugs",response_model=list[DrugBank])
def drugs():
    """Returns drug catalogue"""

    try:
        drug_cat=load_drug_catalogue()

        return drug_cat.to_dict(orient="records")
    except FileNotFoundError as exc:
        logger.exception("Required drug data file was not found.")

        raise HTTPException(
            status_code=500,
            detail="Required drug data is unavailable.",
        ) from exc

    
# product groups end point






@app.get("/inventory/product")
def get_atc_codes():
    
    return [
        {
            "code": code,
            "description": description
        }
        for code, description in ATC_CODES.items()
    ]

