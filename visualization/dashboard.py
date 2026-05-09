import streamlit as st
import pandas as pd
from datetime import datetime
from extraction_pipeline.processor import DataProcessor
from visualization.styles import DashboardStyles
from visualization.charts import ChartGenerator
import extraction_pipeline.analytics as analytics
import visualization.live_tab as live_tab

class RailwayDashboard:
    """Main dashboard application class."""
    
    def __init__(self):
        self.styles = DashboardStyles()
        self.charts = ChartGenerator()
        self.processor = DataProcessor()
        self.available_lines = {
            "Train No. 31 (Special Express)": "./extracted_data/station_delays_line31.csv",
            "Train No. 169 (Rapid)": "./extracted_data/station_delays_line169.csv"
        }

    def render_sidebar(self):
        """Render the sidebar configuration menu."""
        st.sidebar.markdown("## Configuration")
        
        selected_labels = st.sidebar.multiselect(
            "Select Train Lines to Compare",
            options=list(self.available_lines.keys()),
            default=list(self.available_lines.keys())
        )
        
        # Load Data
        selected_files = {label: self.available_lines[label] for label in selected_labels}
        df = self.processor.load_selected_lines(selected_files)
        
        if df is None:
            return None, None, None, None

        # Filter Setup
        all_stations = sorted(df['station_name'].unique())
        selected_stations = st.sidebar.multiselect(
            "Stations of Interest",
            options=all_stations,
            default=[s for s in ["ชุมทางทุ่งสง"] if s in all_stations]
        )

        freq_options = {"Daily View": "D", "Monthly Average": "ME", "Yearly Summary": "YE"}
        selected_freq_label = st.sidebar.selectbox("Time Granularity", list(freq_options.keys()))
        freq_code = freq_options[selected_freq_label]

        delay_threshold = st.sidebar.slider("Risk Threshold (min)", 0, 180, 30, 5)

        min_date, max_date = df['date'].min().date(), df['date'].max().date()
        date_range = st.sidebar.date_input("Analysis Period", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        # Apply Filters
        if len(date_range) == 2:
            filtered_df = self.processor.filter_data(df, selected_stations, date_range)
        else:
            filtered_df = df # Fallback if range selection is incomplete

        return df, filtered_df, freq_code, delay_threshold, selected_labels, selected_stations

    def render_hero(self, selected_labels):
        """Render the landing hero section."""
        line_display = " & ".join([label.split(" ")[-1].strip("()") for label in selected_labels]) if selected_labels else "Railway"
        st.markdown(f"""
            <div class="hero-container">
                <div class="hero-title">{line_display} Analytics Comparison</div>
                <p style="color: #64748b; font-size: 1.1rem; font-weight: 300;">Journey reliability intelligence for Thai Railways</p>
            </div>
        """, unsafe_allow_html=True)

    def render_metrics(self, df, filtered_df):
        """Render key performance indicator cards."""
        for line in df['line'].unique():
            line_df = filtered_df[filtered_df['line'] == line]
            if line_df.empty: continue
            
            st.markdown(f"#### Train No. {line} Performance")
            m1, m2, m3, m4 = st.columns(4)
            
            with m1: self.styles.custom_metric("Worst Lateness", f"{line_df['arr_delay'].max():.0f}m")
            with m2: 
                ci_low, ci_high = line_df['arr_delay'].quantile(0.05), line_df['arr_delay'].quantile(0.95)
                self.styles.custom_metric("CI 90% Range", f"{ci_low:.0f}m - {ci_high:.0f}m")
            with m3: self.styles.custom_metric("Average Delay", f"{line_df['arr_delay'].mean():.1f}m")
            with m4: self.styles.custom_metric("Major Delays (>1h)", f"{(line_df['arr_delay'] > 60).sum()}")
        st.markdown("<br>", unsafe_allow_html=True)

    def run(self):
        """Execute the dashboard application."""
        self.styles.apply_styles()
        
        df, filtered_df, freq_code, delay_threshold, selected_labels, selected_stations = self.render_sidebar()
        
        if df is None:
            st.warning("Please select at least one train line to begin analysis.")
            return

        self.render_hero(selected_labels)
        self.render_metrics(df, filtered_df)

        # Tabs
        tab_live, tab_trends, tab_dist, tab_causes = st.tabs(["Live Status", "Performance Trends", "Delay Distribution", "Reason Logs"])

        with tab_live:
            live_tab.render_live_tab()

        with tab_trends:
            st.markdown("### Historical performance trends over time")
            fig_trends = self.charts.plot_performance_trends(filtered_df, selected_stations, freq_code)
            if fig_trends: st.plotly_chart(fig_trends, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Day-of-week breakdown comparison")
            all_dow_stats = []
            for line in df['line'].unique():
                line_df = filtered_df[filtered_df['line'] == line]
                if line_df.empty: continue
                stats = analytics.compute_dow_stats(line_df, on_time_threshold=delay_threshold).reset_index()
                stats['line'] = line
                all_dow_stats.append(stats)
            
            if all_dow_stats:
                combined_dow = pd.concat(all_dow_stats)
                st.plotly_chart(self.charts.plot_dow_comparison(combined_dow, "median"), use_container_width=True)
                st.plotly_chart(self.charts.plot_dow_comparison(combined_dow, "mean"), use_container_width=True)
                st.plotly_chart(self.charts.plot_extreme_risk(combined_dow), use_container_width=True)
                
                with st.expander("Detailed Day-of-Week Comparison Table"):
                    st.dataframe(combined_dow.round(2), use_container_width=True, hide_index=True)

        with tab_dist:
            st.markdown("### Lateness Distribution & Risk Profile")
            col_hist, col_risk = st.columns([2, 1])
            with col_hist:
                st.plotly_chart(self.charts.plot_lateness_distribution(filtered_df), use_container_width=True)
            with col_risk:
                # Reuse existing risk assessment logic...
                self.render_risk_assessment(df, selected_stations, delay_threshold)

        with tab_causes:
             # Reuse existing cause analysis logic...
             self.render_cause_analysis(filtered_df)

    def render_risk_assessment(self, df, selected_stations, delay_threshold):
        target_station = "ชุมทางทุ่งสง"
        st.markdown(f'<div style="background: #f8fafc; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; margin-top: 2rem;"><h3 style="margin-top:0; color: #1e40af;">Risk Assessment</h3>', unsafe_allow_html=True)
        if target_station in selected_stations:
            ts_df = df[df['station_name'] == target_station]
            risk = (ts_df['arr_delay'] > delay_threshold).mean() * 100
            st.write(f"Based on {len(ts_df)} observations for {target_station}:")
            st.metric(f"Probability of >{delay_threshold}m Delay", f"{risk:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    def render_cause_analysis(self, filtered_df):
        if 'delay_cause_th' in filtered_df.columns:
            major_incidents_df = filtered_df[filtered_df['arr_delay'] > 60].sort_values('arr_delay', ascending=False)
            if not major_incidents_df.empty:
                st.markdown("### Major Incidents (> 1 Hour)")
                st.dataframe(major_incidents_df[['date', 'station_name', 'arr_delay', 'delay_cause_th', 'delay_cause_en']], use_container_width=True, hide_index=True)
