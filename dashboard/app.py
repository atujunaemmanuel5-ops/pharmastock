import streamlit as st
import requests

# Page configuration
st.set_page_config(
    page_title="PharmaStock AI",
    page_icon="💊",
    layout="wide",
)

API_URL = "http://127.0.0.1:8000"

# Dashboard heading
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
    return response.json()


def get_stock_summary():
    """Retrieve stock summaries from the FastAPI backend."""
    response = requests.get(
        f"{API_URL}/inventory/stock-summary",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


try:
    expiry_records = get_expiry_records()
    stock_records = get_stock_summary()

    expired_count = sum(
        record["expiry_status"] == "Expired"
        for record in expiry_records
    )

    expiring_soon_count = sum(
        record["expiry_status"] == "Expiring soon"
        for record in expiry_records
    )

    total_stock_records = len(stock_records)

    # Key metrics
    st.subheader("Inventory Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Expired Batches", expired_count)

    with col2:
        st.metric("Expiring Soon", expiring_soon_count)

    with col3:
        st.metric("Stock Records", total_stock_records)

    st.divider()

    # Expiry table
    st.subheader("Expiry Monitoring")

    if expiry_records:
        st.dataframe(
            expiry_records,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No expiry records were returned by the API.")

    # Simulation notice
    if any(record.get("is_simulated", False) for record in expiry_records):
        st.warning(
            "Demonstration data: the expiry records include simulated "
            "inventory. Do not use these figures for real dispensing "
            "or clinical decisions."
        )

except requests.RequestException:
    st.error(
        "Unable to connect to the PharmaStock AI backend. "
        "Check that FastAPI is running and try again."
    )
except (KeyError, TypeError, ValueError):
    st.error(
        "The backend returned data in an unexpected format. "
        "Please check the API response."
    )