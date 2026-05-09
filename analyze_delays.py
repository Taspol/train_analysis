import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import live_view

# Page configuration
st.set_page_config(
    page_title="Train Reliability Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Light Design System (Custom CSS)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* Global styles */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .main {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        color: #1e293b;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Header styling */
    .hero-container {
        padding: 2.5rem;
        background: #ffffff;
        border-radius: 1.5rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px -5px rgba(0, 0, 0, 0.05);
    }

    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }

    /* Card styling */
    .metric-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 1.25rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-4px);
        border-color: #3b82f6;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }

    .metric-label {
        color: #64748b;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
    }

    .metric-value {
        color: #0f172a;
        font-size: 1.875rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #ffffff;
        border-radius: 0.75rem 0.75rem 0 0;
        padding: 0 1.5rem;
        color: #64748b;
        border: 1px solid #e2e8f0;
    }

    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }
    
    /* Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_path = 'station_delays.csv'
    try:
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        df['arr_delay'] = pd.to_numeric(df['arr_delay'], errors='coerce').fillna(0)
        df['dep_delay'] = pd.to_numeric(df['dep_delay'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def custom_metric(label, value, status="info"):
    st.markdown(f"""
        <div class="metric-card">
            <span class="metric-label">{label}</span>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def main():
    # Hero Section
    st.markdown("""
        <div class="hero-container">
            <div class="hero-title">169Railway Analytics</div>
            <p style="color: #64748b; font-size: 1.1rem; font-weight: 300;">Journey reliability intelligence for Thai Railways</p>
        </div>
    """, unsafe_allow_html=True)

    df = load_data()
    if df is None:
        st.warning("Data source not found. Please ensure 'station_delays.csv' is generated.")
        return

    # Sidebar styling
    st.sidebar.markdown("## Configuration")
    
    all_stations = sorted(df['station_name'].unique())
    default_stations = ["ชุมทางทุ่งสง"]
    
    selected_stations = st.sidebar.multiselect(
        "Stations of Interest",
        options=all_stations,
        default=[s for s in default_stations if s in all_stations]
    )

    freq_options = {"Daily View": "D", "Monthly Average": "ME", "Yearly Summary": "YE"}
    selected_freq_label = st.sidebar.selectbox("Time Granularity", list(freq_options.keys()))
    freq_code = freq_options[selected_freq_label]

    delay_threshold = st.sidebar.slider(
        "Risk Threshold (minutes)",
        min_value=0,
        max_value=180,
        value=30,
        step=5,
        help="Set the lateness threshold to calculate the probability of significant delay."
    )

    # Date Range Filter
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    selected_dates = st.sidebar.date_input(
        "Analysis Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Information")
    st.sidebar.info("""
        **90% Range**: The window of time where 90% of historical trips arrived (5th to 95th percentile).
        
        This tool analyzes historical delay patterns to help you plan your journey with confidence.
    """)

    if not selected_stations:
        st.info("Welcome! Please select one or more stations in the sidebar to visualize performance data.")
        return

    # Apply Filters
    mask = (df['station_name'].isin(selected_stations))
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
        mask &= (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    
    filtered_df = df[mask]

    # --- Metrics Section ---
    m1, m2, m3, m4 = st.columns(4)
    
    max_delay = filtered_df['arr_delay'].max()
    avg_delay = filtered_df['arr_delay'].mean()
    major_delays_count = (filtered_df['arr_delay'] > 60).sum()
    
    # Calculate 90% Confidence Interval (Percentile based for better practical use)
    ci_lower = filtered_df['arr_delay'].quantile(0.05)
    ci_upper = filtered_df['arr_delay'].quantile(0.95)

    with m1: custom_metric("Worst Lateness", f"{max_delay:.0f}m")
    with m2: custom_metric("CI 90% Range", f"{ci_lower:.0f}m - {ci_upper:.0f}m")
    with m3: custom_metric("Average Delay", f"{avg_delay:.1f}m")
    with m4: custom_metric("Major Delays (>1h)", f"{major_delays_count}")

    st.markdown("<br>", unsafe_allow_html=True)


    # --- Main Analysis Area ---
    tab_live, tab_trends, tab_dist, tab_causes = st.tabs([
        "Live Status",
        "Performance Trends",
        "Delay Distribution",
        "Reason Logs"
    ])

    with tab_live:
        live_view.render_live_tab()

    with tab_trends:
        st.markdown("### Historical performance trends over time")
        plot_df = filtered_df.copy().set_index('date')
        resampled_data = []
        for station in selected_stations:
            station_data = plot_df[plot_df['station_name'] == station]['arr_delay'].resample(freq_code).mean().reset_index()
            station_data['station_name'] = station
            resampled_data.append(station_data)
        
        final_plot_df = pd.concat(resampled_data)

        fig_line = px.line(
            final_plot_df, 
            x='date', 
            y='arr_delay', 
            color='station_name',
            labels={'arr_delay': 'Average Delay (minutes)', 'date': 'Timeline'},
            template="plotly_white",
            color_discrete_sequence=["#3b82f6", "#8b5cf6", "#f43f5e", "#10b981", "#f59e0b"]
        )
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Outfit",
            hovermode="x unified",
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Minutes")
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with tab_dist:
        st.markdown("### Lateness Distribution & Risk Profile")
        col_hist, col_risk = st.columns([2, 1])

        with col_hist:
            fig_hist = px.histogram(
                filtered_df,
                x="arr_delay",
                color="station_name",
                marginal="box",
                nbins=40,
                template="plotly_white",
                barmode="overlay",
                color_discrete_sequence=["#3b82f6", "#8b5cf6"]
            )
            fig_hist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_family="Outfit",
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Delay Duration (Minutes)",
                yaxis_title="Frequency"
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_risk:
            st.markdown("""
                <div style="background: #f8fafc; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; margin-top: 2rem;">
                    <h3 style="margin-top:0; color: #1e40af;">Risk Assessment</h3>
            """, unsafe_allow_html=True)
            
            target_station = "ชุมทางทุ่งสง"
            if target_station in selected_stations:
                ts_df = df[df['station_name'] == target_station]
                high_delay = (ts_df['arr_delay'] > delay_threshold).sum()
                risk = (high_delay / len(ts_df)) * 100
                st.write(f"Based on {len(ts_df)} observations for {target_station}:")
                st.metric(f"Probability of >{delay_threshold}m Delay", f"{risk:.1f}%")
                
                if risk < 10:
                    st.info(f"High Reliability: Low chance of exceeding {delay_threshold}m.")
                elif risk < 25:
                    st.warning(f"Moderate Variation: Occasional delays >{delay_threshold}m occur.")
                else:
                    st.error(f"High Delay Risk: Frequent delays exceeding {delay_threshold}m.")
            else:
                st.write(f"Add {target_station} to view specific risk analytics.")
            
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_causes:
        if 'delay_cause_th' in df.columns:
            # Major Delays (> 1 hour)
            major_incidents_df = filtered_df[filtered_df['arr_delay'] > 60].sort_values('arr_delay', ascending=False)
            
            if not major_incidents_df.empty:
                st.markdown("### Major Incidents (> 1 Hour)")
                st.markdown("Detailed breakdown of trips with critical timing failures and their reported causes.")
                st.dataframe(
                    major_incidents_df[['date', 'station_name', 'arr_delay', 'delay_cause_th', 'delay_cause_en']],
                    use_container_width=True,
                    hide_index=True
                )
                st.markdown("---")

            # General Delay Causes
            causes_df = filtered_df[filtered_df['delay_cause_th'].notna() & (filtered_df['delay_cause_th'] != "None") & (filtered_df['delay_cause_th'] != "")]
            
            if not causes_df.empty:
                st.markdown("### Root Cause Analysis")
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    cause_counts = causes_df['delay_cause_th'].value_counts().reset_index()
                    cause_counts.columns = ['Cause', 'Occurrences']
                    fig_pie = px.pie(
                        cause_counts.head(6),
                        values='Occurrences',
                        names='Cause',
                        hole=0.6,
                        template="plotly_white",
                        color_discrete_sequence=px.colors.sequential.Blues_r
                    )
                    fig_pie.update_layout(
                        showlegend=True,
                        legend=dict(orientation="h", y=-0.1),
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with c2:
                    st.markdown("#### Primary Disturbance Factors")
                    st.info("The chart on the left illustrates the most frequent reasons cited for delays across all selected stations.")
                    st.write("Common patterns include construction maintenance and waiting for track clearance.")
            else:
                st.info("No recorded delay cause data found for the current selection.")

if __name__ == "__main__":
    main()
