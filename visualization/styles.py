import streamlit as st

class DashboardStyles:
    """Class to manage CSS and visual styling of the dashboard."""
    
    @staticmethod
    def apply_styles():
        """Inject custom CSS for the modern light design system."""
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

    @staticmethod
    def custom_metric(label, value):
        """Render a custom HTML-based metric card."""
        st.markdown(f"""
            <div class="metric-card">
                <span class="metric-label">{label}</span>
                <div class="metric-value">{value}</div>
            </div>
        """, unsafe_allow_html=True)
