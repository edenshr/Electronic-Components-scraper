import pandas as pd
import numpy as np
import datetime, time
from dateutil.relativedelta import relativedelta

def scoring(product_df: pd.DataFrame) -> int:
    cur_date = datetime.datetime.now()
    prev_week = cur_date - relativedelta(days=7)
    prev_month_3 = cur_date - relativedelta(months=3)
    prev_month_6 = cur_date - relativedelta(months=6)
    product_df["Date"] = pd.to_datetime(product_df["Date"])
    product_df = product_df.set_index("Date")
    filtered_3_month_df = product_df.loc[prev_month_3.date():]
    filtered_prev_week_df = product_df.loc[prev_week.date():]
    value_3_month_counts = filtered_3_month_df["Searches"].value_counts(normalize=True)
    value_prev_week_counts = filtered_prev_week_df["Searches"].value_counts(normalize=True)
    if value_3_month_counts.loc[0] > 0.9 and value_prev_week_counts.loc[0] > 0.71:
        scoring = 0
    else:
        filtered_last_n_month = product_df.loc[prev_month_6.date():].copy()
        filtered_last_n_month['EwM'] = filtered_last_n_month["Searches"].ewm(span=30, adjust=False).mean()
        scoring = float(filtered_last_n_month['EwM'].iloc[-1])
    return scoring
