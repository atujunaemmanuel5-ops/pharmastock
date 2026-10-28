# Step 1: Import FastAPI.

from os import stat

from fastapi import FastAPI

# Step 2: Import HTTPException from FastAPI for handling errors.
from fastapi import HTTPException


# Step 3: Import the two inventory functions from src.inventory.
from api.schemas import ExpiryRecord, StockSummaryRecord
from src.inventory import load_inventory_batches,create_expiry_report,summarize_stock

# Step 4: Create the FastAPI application object.
app= FastAPI()

# Step 5: Register a GET endpoint at /health.
@app.get("/health")
def health_status():

#         Return a small dictionary confirming the API is running.
    return {
        "status":"ok"
    }

# Step 6: Register a GET endpoint at /inventory/expiry.
@app.get("/inventory/expiry",response_model=list[ExpiryRecord])

def expiry_report():
    try:


# Step 7: Inside the expiry endpoint:

#         a. Load inventory batches.
        batches=load_inventory_batches()
#         b. Generate the expiry report.
        report=create_expiry_report(batches)
#         c. Convert the DataFrame into a list of dictionaries.
        records=report.to_dict(orient="records")
#         d. Return the records.
        return records
    
    except Exception:
        raise HTTPException(
        status_code=500,
        detail="Could not generate expiry report"
    )




# 3. Import the existing inventory functions:
#    - load_inventory_batches
#    - the function that summarises stock in src/inventory.py


# 4. Create the GET endpoint.
@app.get("/inventory/stock-summary",response_model=list[StockSummaryRecord])
#    Route: /inventory/stock-summary
#    Tell FastAPI which response model the endpoint returns.



# 5. Define the endpoint function.
def stock_summary():
    # 6. Start a try block to handle unexpected errors.
        try:
             

        # 7. Load the inventory batches into a DataFrame.
            batches=load_inventory_batches()

        # 8. Pass the DataFrame to the existing stock-summary function.
            stock=summarize_stock(batches)

        #    Remember: business logic belongs in src/inventory.py,
        #    not inside this API endpoint.

        # 9. Convert the resulting DataFrame into a list of dictionaries.
        #    Each dictionary should represent one drug's stock summary.
            records=stock.to_dict(orient="records")

        # 10. Return the records.
            return records


    # 11. If something unexpected goes wrong, raise an HTTPException.
    #     Use an appropriate status code and a safe error message.
        except Exception:
             raise HTTPException(
                  status_code=200,
                  detail="Could not generate stock summary")

