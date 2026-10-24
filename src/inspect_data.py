"""This file handles data inpsection nothing much"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def inspect_csv(hourly_sales_path:str):
    """This function inspects hourly csv data"""

    # Loading file path
    file_path=Path(hourly_sales_path)

    # Data loading
    df=pd.read_csv(file_path)

    # Information overview of the dataset
    
    number_of_rows = df.shape[0]
    number_of_columns = df.shape[1]


    # Inspection metrics
    print("-"*40)
    print(f"First five rows of {file_path.name} file")
    print("-"*40)
    print(f"\n{df.head()}")

    # Displaying number of rows and columns of this dataset
    
    print(f"===========Total number of rows and columns=============")
    print(f"\nNumber of rows: {number_of_rows} ")
    print(f"\nNumber of columns: {number_of_columns}")

    # Displaying brief overview of the dataset
    print("=========================================================")
    print(f"Brief overview of the {file_path.name} dataset")
    print("=========================================================\n")
    print(f"{df.info()}")

    # Checking for missing values
    print("============================================================")
    print("Missing values And duplicates")
    print(f"Total number of missing values: {df.isnull().sum()}")
    print(f"Total number of duplicated rows: {df.duplicated().sum()}")









inspect_csv("data/raw/synthetic_data/drugs.csv")
