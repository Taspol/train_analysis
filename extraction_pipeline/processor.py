import pandas as pd
import streamlit as st
import os
import re
from typing import List, Dict, Optional

class DataProcessor:
    """Class to handle data loading and preprocessing."""
    
    @staticmethod
    @st.cache_data
    def load_selected_lines(selected_files: Dict[str, str]) -> Optional[pd.DataFrame]:
        """Load multiple train line CSV files and combine them."""
        if not selected_files:
            return None
            
        all_dfs = []
        for label, file_path in selected_files.items():
            try:
                if not os.path.exists(file_path):
                    st.error(f"File not found: {file_path}")
                    continue
                    
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])
                df['arr_delay'] = pd.to_numeric(df['arr_delay'], errors='coerce').fillna(0)
                df['dep_delay'] = pd.to_numeric(df['dep_delay'], errors='coerce').fillna(0)
                
                # Extract digits from the label (e.g. "31" from "Train No. 31")
                line_match = re.search(r'\d+', label)
                line_num = line_match.group(0) if line_match else label
                df['line'] = f"No. {line_num}"
                all_dfs.append(df)
            except Exception as e:
                st.error(f"Error loading {file_path}: {e}")
                
        if not all_dfs:
            return None
            
        return pd.concat(all_dfs, ignore_index=True)

    @staticmethod
    def filter_data(df: pd.DataFrame, stations: List[str], date_range: tuple) -> pd.DataFrame:
        """Filter the combined dataframe based on UI selections."""
        if df is None: return None
        
        start_date, end_date = date_range
        mask = (
            (df['station_name'].isin(stations)) &
            (df['date'].dt.date >= start_date) &
            (df['date'].dt.date <= end_date)
        )
        return df[mask]
