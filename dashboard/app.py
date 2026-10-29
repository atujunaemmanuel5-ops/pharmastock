import os

import requests
import streamlit as st


# Page configuration
st.set_page_config(
    page_title="PharmaStock AI",
    page_icon="💊",
    layout="wide",
)

# Read the backend address from an environment variable.
API_URL = os.getenv(
    "PHARMASTOCK_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


st.title("💊 PharmaStock AI")
st.caption("Pharmacy Inventory Intelligence Dashboard")
st.divider()


def get_expiry_records():
    """Retrieve expiry records from the FastAPI backend."""

    response = requests.get(
        f"{API_URL}/inventory/expiry",
        timeout=10,
    )
    response.raise_for_status()

    records = response.json()

    if not isinstance(records, list):
        raise ValueError("Expiry response must be a list.")

    return records


def get_stock_summary():
    """Retrieve stock summaries from the FastAPI backend."""

    response = requests.get(
        f"{API_URL}/inventory/stock-summary",
        timeout=10,
    )
    response.raise_for_status()

    records = response.json()

    if not isinstance(records, list):
        raise ValueError("Stock summary response must be a list.")

    return records


# Load expiry records independently.
expiry_records = None

try:
    expiry_records = get_expiry_records()

except requests.RequestException:
    st.error(
        "Unable to load expiry information. "
        "Check that the backend is running and inspect its logs."
    )

except (ValueError, TypeError):
    st.error(
        "The expiry endpoint returned data in an unexpected format."
    )


# Load stock records independently.
stock_records = None

try:
    stock_records = get_stock_summary()

except requests.RequestException:
    st.error(
        "Unable to load stock summaries. "
        "Check that the backend is running and inspect its logs."
    )

except (ValueError, TypeError):
    st.error(
        "The stock-summary endpoint returned data in an unexpected format."
    )


# Inventory overview
st.subheader("Inventory Overview")

col1, col2, col3, col4 = st.columns(4)

if expiry_records is not None:
    expired_count = sum(
        record["expiry_status"] == "Expired"
        for record in expiry_records
    )

    critical_count = sum(
        record["expiry_status"] == "Critical"
        for record in expiry_records
    )

    watch_count = sum(
        record["expiry_status"] == "Watch"
        for record in expiry_records
    )

    with col1:
        st.metric("Expired Batches", expired_count)

    with col2:
        st.metric("Critical Batches", critical_count)

    with col3:
        st.metric("Watch Batches", watch_count)

    with col4:
        st.metric("Batches Monitored", len(expiry_records))

else:
    st.info("Expiry metrics are unavailable.")


# Stock quantities
st.divider()
st.subheader("Stock Summary")

if stock_records is not None:
    total_physical_stock = sum(
        record["total_stock"]
        for record in stock_records
    )

    total_usable_stock = sum(
        record["usable_stock"]
        for record in stock_records
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Physical Stock",
            f"{total_physical_stock:,}",
        )

    with col2:
        st.metric(
            "Usable Stock",
            f"{total_usable_stock:,}",
        )

    with col3:
        st.metric(
            "Drug Records",
            len(stock_records),
        )

    st.dataframe(
        stock_records,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("Stock summary is unavailable.")


# Expiry monitoring
st.divider()
st.subheader("Expiry Monitoring")

if expiry_records is not None:
    if expiry_records:
        st.dataframe(
            expiry_records,
            use_container_width=True,
            hide_index=True,
        )

        # Warn users when any returned batch uses simulated data.
        if any(
            record.get("is_simulated", False)
            for record in expiry_records
        ):
            st.warning(
                "Demonstration data: this inventory includes simulated "
                "records. Do not use these figures for real dispensing "
                "or clinical decisions."
            )

    else:
        st.info("No inventory batches were returned.")

else:
    st.info("Expiry information is unavailable.")