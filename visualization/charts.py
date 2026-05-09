import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import extraction_pipeline.analytics as analytics

class ChartGenerator:
    """Class to generate all Plotly charts for the dashboard."""
    
    @staticmethod
    def plot_performance_trends(df, stations, freq_code):
        """Generate a multi-line chart for historical performance trends."""
        plot_df = df.copy().set_index('date')
        resampled_data = []
        
        for (station, line), group in plot_df.groupby(['station_name', 'line']):
            station_line_data = group['arr_delay'].resample(freq_code).mean().reset_index()
            station_line_data['station_name'] = station
            station_line_data['line'] = line
            station_line_data['display_name'] = f"{line} - {station}"
            resampled_data.append(station_line_data)
        
        if not resampled_data:
            return None
            
        final_plot_df = pd.concat(resampled_data)
        fig = px.line(
            final_plot_df, 
            x='date', 
            y='arr_delay', 
            color='display_name',
            labels={'arr_delay': 'Average Delay (min)', 'date': 'Timeline', 'display_name': 'Train Line & Station'},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Outfit",
            hovermode="x unified",
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Minutes")
        )
        return fig

    @staticmethod
    def plot_dow_comparison(combined_dow, metric="median"):
        """Generate a grouped bar chart for Day-of-Week comparison."""
        fig = px.bar(
            combined_dow,
            x="day_of_week",
            y=metric,
            color="line",
            barmode="group",
            category_orders={"day_of_week": analytics.DOW_ORDER},
            labels={metric: f"{metric.capitalize()} Delay (min)", "day_of_week": "Day of week", "line": "Train Line"},
            template="plotly_white",
            color_discrete_sequence=["#3b82f6", "#f43f5e"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Outfit",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig

    @staticmethod
    def plot_extreme_risk(combined_dow):
        """Generate a line chart for 95th percentile risk comparison."""
        fig = px.line(
            combined_dow,
            x="day_of_week",
            y="p95",
            color="line",
            markers=True,
            category_orders={"day_of_week": analytics.DOW_ORDER},
            labels={"p95": "95th Percentile Delay (min)", "day_of_week": "Day of week"},
            title="Extreme Delay Risk (95th Percentile) by Day",
            template="plotly_white",
            color_discrete_sequence=["#3b82f6", "#f43f5e"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Outfit",
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig

    @staticmethod
    def plot_lateness_distribution(df):
        """Generate a histogram for lateness distribution."""
        fig = px.histogram(
            df,
            x="arr_delay",
            color="line",
            marginal="box",
            nbins=40,
            template="plotly_white",
            barmode="overlay",
            labels={'arr_delay': 'Delay (min)', 'line': 'Train Line'},
            color_discrete_sequence=["#3b82f6", "#f43f5e"]
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Outfit",
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Delay Duration (Minutes)",
            yaxis_title="Frequency"
        )
        return fig
