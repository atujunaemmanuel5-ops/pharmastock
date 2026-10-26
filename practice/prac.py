"""This file handles data preparstion for later usage"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def converting_dates(file_path:str)->pd.DataFrame:
    """This function converts dates from string to dates"""

    # Loading file path
    dir_path= Path(file_path)

    df=pd.read_csv(dir_path)

    
    

    #Coverting the date
    df["date"]=pd.to_datetime(df["datum"],format="mixed") # Setting date format with wild cards
    df.info()

    #print(df["date"].min())
    #print(df["date"].max())

    # Selecting date range
    #start_date = pd.Timestamp("2015-01-02")
    #end_date = pd.Timestamp("2019-01-04")

    #selected = df.loc[
    #    df["date"].between(start_date, end_date)
    #]

    #print(selected)

    # Sorting date values 
    #df=df.sort_values(by="date")
    #df.head()

    # Checking for duplicates in dates
    duplicates = df["date"].duplicated(keep=False)

    print(df.loc[duplicates])
    

    


converting_dates("data/raw/salesweekly.csv")





