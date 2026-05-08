# 🚆 Thai Railway Reliability Intelligence

An advanced data scraping and analysis suite designed to quantify and visualize train delays for the Thai Railway system. This project specifically focuses on the route between **Bangkok (Krung Thep Aphiwat)** and **Thung Song Junction**.

## 📌 Project Overview

This tool allows users to:
1.  **Scrape**: Extract historical tracking data from the official Thai Railway TTS API.
2.  **Analyze**: Process lateness patterns across hundreds of historical trips.
3.  **Visualize**: Interact with a modern dashboard to evaluate travel risks and identify common causes of delays.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.8+ installed. You will also need the following libraries:
```bash
pip install pandas plotly streamlit requests
```

### 2. Data Collection (Scraping)
The scraper uses a predefined mapping of dates and runhashes to fetch specific tracking information.
-   **Script**: `scrape_delays.py`
-   **Input**: `date_runhash_map.csv`
-   **Execution**:
    ```bash
    python3 scrape_delays.py
    ```
-   **Output**: Generates `station_delays.csv` containing arrival/departure lateness and reported delay causes.

### 3. Launching the Analytics Dashboard
The interactive dashboard is built with Streamlit and provides a premium light-themed interface.
-   **Script**: `analyze_delays.py`
-   **Execution**:
    ```bash
    streamlit run analyze_delays.py
    ```

---

## 📊 Analyzer Features

### 🔍 Configuration Sidebar
-   **Station Selector**: Compare performance across multiple stations simultaneously.
-   **Time Granularity**: View data in Daily, Monthly, or Yearly averages.
-   **Risk Threshold (N)**: Set your custom lateness threshold (e.g., 30 mins) to calculate probability of failure.
-   **Analysis Period**: Select a specific historical date range for focused research.

### 📈 Performance Metrics
-   **Worst/Best Lateness**: Identify the extreme outliers in the dataset.
-   **Reliability Score**: Percentage of trips arriving within a 10-minute window of the schedule.
-   **Major Delays Counter**: Instant count of incidents exceeding 1 hour.

### 🧠 Intelligence Logs
-   **Root Cause Analysis**: A breakdown of official reasons for delays (e.g., track clearance, construction).
-   **Major Incidents (>1h)**: A dedicated deep-dive table for critical timing failures, showing exactly what went wrong and when.

---

## 📁 File Structure
-   `scrape_delays.py`: Python script for automated data extraction.
-   `analyze_delays.py`: Streamlit-based intelligence dashboard.
-   `station_delays.csv`: The primary dataset (generated after scraping).
-   `date_runhash_map.csv`: Mapping file required for API queries.
-   `station_data.json`: Metadata for railway stations.

---

## ⚖️ Disclaimer
This tool is intended for personal analysis and journey planning. It relies on publicly available data from the Thai Railway API. Arrival times are subject to real-time changes and operational incidents.
