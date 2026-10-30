"""
Central configuration for PharmaStock AI.

This file stores settings used by other project files, including:
- File paths
- Raw dataset column names
- Processed dataset column names
- Decisions about partial days

Keeping these settings in one place makes the project easier to maintain.
For example, if the dataset's date column changes, update DATE_COLUMN here
instead of searching through every Python file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------
# 1. PROJECT PATHS
# ---------------------------------------------------------------------

# __file__ is the location of this config.py file.
# parents[1] moves up two levels:
#   config.py -> src -> project root
#
# Path objects are preferable to manually joining paths with "\" or "/",
# because pathlib handles the correct path format for the operating system.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment variables from the .env file in the project root.
# This is useful for settings such as database connection details.
load_dotenv(PROJECT_ROOT / ".env")


# Location of the original, unmodified daily sales dataset.
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "salesdaily.csv"

# Directory where processed datasets will be saved.
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Final cleaned dataset.
PROCESSED_PATH = PROCESSED_DIR / "daily_sales_clean.csv"


# ---------------------------------------------------------------------
# 2. RAW DATASET COLUMN NAMES
# ---------------------------------------------------------------------

# The original dataset uses "datum" for its date column.
DATE_COLUMN = "datum"

# Expected date format in the original CSV.
# For example, "01/02/2014" is interpreted as January 2, 2014.
DATE_FORMAT = "%m/%d/%Y"

# The eight product groups whose sales we want to prepare.
#
# Important:
# These are product groups, not individual medicine names.
# The dataset does not contain individual medicine-level sales or stock
# records, so we must not describe these columns as individual medicines.
SALES_COLUMNS = [
    "M01AB",
    "M01AE",
    "N02BA",
    "N02BE",
    "N05B",
    "N05C",
    "R03",
    "R06",
]


# ---------------------------------------------------------------------
# 3. OUTPUT DATASET COLUMN NAMES
# ---------------------------------------------------------------------

# We will convert the original wide-format dataset into long format.
#
# Original wide format:
# datum       M01AB   M01AE   ...
# 01/02/2014  5.0     3.0     ...
#
# New long format:
# sale_date   product_group   quantity
# 2014-01-02  M01AB            5.0
# 2014-01-02  M01AE            3.0

OUTPUT_DATE_COLUMN = "sale_date"
OUTPUT_GROUP_COLUMN = "product_group"
OUTPUT_VALUE_COLUMN = "quantity"


# ---------------------------------------------------------------------
# 4. PARTIAL-DAY DECISIONS
# ---------------------------------------------------------------------

# The hourly dataset ends at 19:00 on 2019-10-08.
# This suggests that the final date in the daily dataset may be incomplete.
#
# Therefore, the pipeline removes the last date if this setting is True.
# This decision should be documented as an assumption based on the hourly
# dataset, rather than treated as proof that the daily record is invalid.
DROP_LAST_PARTIAL_DAY = True

# The hourly dataset begins at 08:00 on 2014-01-02.
# We do not yet know whether the missing earlier hours represent zero sales
# or simply an incomplete first day.
#
# Keep this False until the source data or documentation confirms that the
# first day's sales are complete or otherwise safe to retain.
DROP_FIRST_PARTIAL_DAY = False


# ---------------------------------------------------------------------
# 5. OPTIONAL DATABASE CONFIGURATION
# ---------------------------------------------------------------------

# Read DATABASE_URL from the .env file if one is configured.
# It can remain None while the project is using CSV files only.
DATABASE_URL = os.getenv("DATABASE_URL")
FORECAST_DIR = PROJECT_ROOT / "data" / "forecasts"
EVALUATION_PATH = FORECAST_DIR / "forecast_evaluation.csv"

# ATC code classification

ATC_CODES = {
    "M01AB": "Anti-inflammatory and antirheumatic products, acetic acid derivatives",
    "M01AE": "Anti-inflammatory and antirheumatic products, propionic acid derivatives",
    "N02BA": "Other analgesics and antipyretics, salicylic acid and derivatives",
    "N02BE": "Other analgesics and antipyretics, pyrazolones and anilides",
    "N05B": "Anxiolytics",
    "N05C": "Hypnotics and sedatives",
    "R03": "Drugs for obstructive airway diseases",
    "R06": "Antihistamines for systemic use",
}

# ---------------------------------------------------------------------
# 6. INVENTORY DATA CONFIGURATION
# ---------------------------------------------------------------------

# Directory containing the synthetic datasets.
SYNTHETIC_DATA_DIR = (
    PROJECT_ROOT / "data" / "raw" / "synthetic_data"
)

# Synthetic inventory datasets.
DRUGS_PATH = SYNTHETIC_DATA_DIR / "drugs.csv"

INVENTORY_BATCHES_PATH = (
    SYNTHETIC_DATA_DIR / "inventory_batches.csv"
)

SALES_DAILY_PATH = (
    SYNTHETIC_DATA_DIR / "sales_daily_simulated.csv"
)

DRUG_SHARES_PATH = SYNTHETIC_DATA_DIR / "drug_shares.csv"

# Column names used by the inventory datasets.
DRUG_ID_COLUMN = "drug_id"
BATCH_ID_COLUMN = "batch_id"
QUANTITY_ON_HAND_COLUMN = "qty_on_hand"
EXPIRY_DATE_COLUMN = "expiry_date"
RECEIVED_DATE_COLUMN = "received_date"
AS_OF_DATE_COLUMN = "as_of_date"
EXPIRY_REPORT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "expiry_report.csv"
)