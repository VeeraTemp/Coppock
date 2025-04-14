import streamlit as st
import pandas as pd
from coppockhistorical import ETFTracker

# Initialize tracker
tracker = ETFTracker()

# Streamlit UI configuration
st.set_page_config(page_title="Crossover Tracker", page_icon="📈", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    /* Sticky header */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {
        position: sticky;
        top: 0;
        background: var(--default-backgroundColor);
        z-index: 999;
        padding-top: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--default-borderColor);
        margin-bottom: 1rem;
    }

    /* Dark theme tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 25px;
        background-color: var(--default-secondaryBackgroundColor);
        border-radius: 8px 8px 0px 0px;
        gap: 10px;
        color: var(--default-textColor);
        border: 1px solid var(--default-borderColor);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--default-backgroundColor);
        color: var(--default-textColor);
        border-bottom: 1px solid var(--default-backgroundColor);
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 8px;
        border: 1px solid var(--default-borderColor);
    }

    /* Section headers */
    .signal-header {
        font-size: 1.2rem;
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        color: var(--default-textColor);
    }

    /* No signals placeholder */
    .no-signals {
        text-align: center;
        padding: 20px;
        border-radius: 8px;
        background-color: var(--default-secondaryBackgroundColor);
        color: var(--default-textColor);
        margin: 1rem 0;
    }

    /* Refresh button container */
    .refresh-container {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Main title and description
st.title("📈 Indicator Crossover Tracker")
st.markdown("""
    <div style='margin-bottom: 2rem;'>
        Track bullish and bearish crossovers for <strong>Coppock Curve</strong> and <strong>MACD (21,8,5)</strong> indicators.<br>
        <small>Data sourced from Yahoo Finance. Updates may lag by 15 minutes.</small>
    </div>
""", unsafe_allow_html=True)

# Tab layout
tab1, tab2 = st.tabs(["🔔 Live Signals", "📅 Historical Analysis"])


def display_signals(signals):
    if not signals:
        st.markdown('<div class="no-signals">No crossover signals detected</div>', unsafe_allow_html=True)
        return

    df = pd.DataFrame(signals)

    # Sort by crossover type (zero first, then signal)
    df['sort_key'] = df['crossover'].apply(lambda x: 0 if x == 'zero' else 1)
    df = df.sort_values(['sort_key', 'type', 'indicator'])

    # Group by signal type first (bullish/bearish)
    for signal_type, type_label, emoji in [('bullish', 'Bullish Signals (Potential Buying Opportunities)', '🟢'),
                                           ('bearish', 'Bearish Signals (Potential Selling Opportunities)', '🔴')]:
        type_df = df[df['type'] == signal_type]

        if not type_df.empty:
            st.markdown(f'<div class="signal-header">{emoji} {type_label}</div>', unsafe_allow_html=True)

            # Display sorted results
            st.dataframe(
                type_df[['symbol', 'indicator', 'crossover']],
                column_config={
                    "symbol": "Symbol",
                    "indicator": "Indicator",
                    "crossover": st.column_config.TextColumn(
                        "Cross Type",
                        help="Zero: Crossing zero line | Signal: MACD crossing its signal line"
                    )
                },
                hide_index=True,
                use_container_width=True
            )


with tab1:
    # Refresh button at top
    st.markdown('<div class="refresh-container">', unsafe_allow_html=True)
    if st.button("🔄 Refresh Signals", key="refresh_live"):
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Current Market Signals")
    st.markdown("""
        <div style='margin-bottom: 1rem;'>
            These signals are generated from the most recent trading data. 
            Bullish signals suggest potential upward momentum, while bearish signals may indicate downward trends.
        </div>
    """, unsafe_allow_html=True)

    # Auto-load data on first render
    with st.spinner("Scanning for latest signals..."):
        signals = tracker.get_crosses()
        display_signals(signals)

with tab2:
    st.subheader("Historical Crossover Analysis")
    st.markdown("""
        <div style='margin-bottom: 1rem;'>
            Analyze past crossover events to identify patterns and validate strategy effectiveness.
        </div>
    """, unsafe_allow_html=True)

    lookback_days = st.slider(
        "Select analysis period (days)",
        1, 365, 30,
        key="hist_lookback",
        help="Number of past days to analyze for crossovers"
    )

    if st.button("🔍 Analyze Historical Data", use_container_width=True):
        with st.spinner(f"Scanning last {lookback_days} days..."):
            results = tracker.get_historical_crosses(lookback_days)
            if results.empty:
                st.warning(f"No crossovers detected in the last {lookback_days} days.")
            else:
                # Group by date
                dates = results['date'].unique()
                for date in sorted(dates, reverse=True):
                    date_data = results[results['date'] == date]

                    st.markdown(f"### 📅 {date}")

                    # Display signals grouped by type and sorted by crossover
                    display_signals(date_data.to_dict('records'))

# Footer with additional info
st.markdown("""
    <div style='margin-top: 3rem; text-align: center; color: var(--default-textColor); font-size: 0.9rem;'>
        <hr style='margin-bottom: 1rem; border-color: var(--default-borderColor);'>
        <strong>Indicator Definitions:</strong><br>
        <strong>Coppock Curve</strong> - Momentum indicator that identifies long-term buying opportunities when it crosses above zero.<br>
        <strong>MACD</strong> - Moving Average Convergence Divergence shows trend changes when the MACD line crosses its signal line or zero.
    </div>
""", unsafe_allow_html=True)