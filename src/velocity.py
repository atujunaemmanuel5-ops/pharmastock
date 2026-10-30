import pandas as pd
from src.config import RAW_DATA_PATH

# calculations
def calculate_daily_velocity(sales, days=7):
    """
    Calculate average daily sales over a selected period.
    """
    # Load sales daily dataset
    df = pd.read_csv(RAW_DATA_PATH)

    pass


def calculate_sales_growth(current_sales, previous_sales):
    """
    Compare current sales against the previous period.
    """

    # Data loading

    pass


def classify_sales_trend(growth_rate):
    """
    Classify sales as increasing, stable or declining.
    """
    pass