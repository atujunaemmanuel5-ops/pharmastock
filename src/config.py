"""Project settings: paths, column names and data-preparation decisions.

Every other file imports from here, so a setting is changed in ONE place.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# --- paths -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")          # reads .env if it exists (it is never committed)

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "salesdaily.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_PATH = PROCESSED_DIR / "daily_sales_clean.csv"

# --- raw file layout  ---------------------------------------
DATE_COLUMN = "datum"
DATE_FORMAT = "%m/%d/%Y"                    # month/day/year, no zero padding, e.g. 1/2/2014
SALES_COLUMNS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]

# --- processed (clean) file layout -------------------------------------------
OUTPUT_DATE_COLUMN = "sale_date"
OUTPUT_GROUP_COLUMN = "product_group"
OUTPUT_VALUE_COLUMN = "quantity"


# The hourly file shows the last day (2019-10-08) stops at 19:00, so its total is incomplete.
DROP_LAST_PARTIAL_DAY = True
# The first day (2014-01-02) starts at 08:00. Hours 0-7 are probably zero-sales night hours,
# so this is False until you prove otherwise from the hourly file.
DROP_FIRST_PARTIAL_DAY = False
# If a whole day is absent from a file, fill it with this value. Justified only by the evidence
# that zeros are recorded values in this dataset (hourly file has every hour, zeros included).
ABSENT_DAY_FILL_VALUE = 0.0

# --- database (None until you create .env) --------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
