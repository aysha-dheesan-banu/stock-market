import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import smtplib
from email.message import EmailMessage
from pathlib import Path
import plotly.graph_objects as go

# ---- Email Setup ----
EMAIL_ADDRESS = "dheesanaysha@gmail.com"  # Replace with your Gmail
EMAIL_PASSWORD = "qaftrficyudwhnsf"     # Replace with your 16-character App Password
RECIPIENT_EMAIL = "232202@slcs.edu.in"  # Replace with your recipient's email

def send_email_alert(subject, body):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = RECIPIENT_EMAIL
        msg.set_content(body)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Email failed: {e}")
        return False

@st.cache_data
def load_data(symbol, period='1mo', interval='1d'):
    df = yf.download(symbol, period=period, interval=interval)
    if not df.empty:
        df = df.reset_index()
        if 'Date' not in df.columns:
            df.rename(columns={'index': 'Date'}, inplace=True)
    return df

# ---- UI Setup ----
st.set_page_config(page_title="📈 Smart Stock Dashboard", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f3f7fa; }
    h1 { color: #1a237e; font-family: 'Trebuchet MS'; }
    .stButton>button {
        background-color: #1976d2;
        color: white;
        padding: 10px;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💼 Smart Stock Dashboard with Email Alerts")

# ---- Sidebar Configuration ----
st.sidebar.header("🔧 Configure Stock")
symbol = st.sidebar.text_input("📌 Stock Symbol", "AAPL")
period = st.sidebar.selectbox("⏳ Period", ['1d', '5d', '1mo', '3mo', '6mo', '1y'])
interval = st.sidebar.selectbox("⏱️ Interval", ['1h', '1d', '1wk'])
chart_type = st.sidebar.radio("📊 Chart Type", ['Line', 'Bar', 'Area', 'Candlestick'])
show_ma = st.sidebar.checkbox("📈 Show 20-Day Moving Average")
show_info = st.sidebar.checkbox("📋 Show Company Info")

# ---- Load Data ----
if symbol:
    data = load_data(symbol, period, interval)

    if data.empty or 'Date' not in data.columns:
        st.warning("⚠️ No data available. Try changing the interval or check the stock symbol.")
    else:
        col1, col2 = st.columns([3, 2])

        # --- Main Price Chart ---
        with col1:
            st.subheader(f"📊 {symbol.upper()} Price Chart")
            fig = go.Figure()

            if chart_type == 'Line':
                fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], mode='lines', name='Close Price'))

            elif chart_type == 'Bar':
                fig.add_trace(go.Bar(x=data['Date'], y=data['Close'], name='Close Price', marker_color='blue'))

            elif chart_type == 'Area':
                fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], mode='lines', fill='tozeroy', name='Close Price'))

            elif chart_type == 'Candlestick':
                if all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
                    fig.add_trace(go.Candlestick(
                        x=data['Date'],
                        open=data['Open'],
                        high=data['High'],
                        low=data['Low'],
                        close=data['Close'],
                        name='Candlestick'
                    ))
                else:
                    st.warning("⚠️ Candlestick data not available for this symbol/interval.")

            if show_ma and 'Close' in data.columns:
                data['MA20'] = data['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(x=data['Date'], y=data['MA20'], name='20-Day MA'))

            fig.update_layout(title=f"{symbol.upper()} Price Chart", xaxis_title="Date", yaxis_title="Price",
                              height=400, margin=dict(t=30, b=30))
            st.plotly_chart(fig, use_container_width=True)

        # --- Metrics and Volume ---
        with col2:
            try:
                current = float(data['Close'].iloc[-1])
                prev = float(data['Close'].iloc[-2])
                delta = round(current - prev, 2)
                st.metric("💰 Current Price", f"${current:.2f}", delta=f"{delta:+.2f}")

                # Alerts
                if delta > 2:
                    st.success("📈 Price Surge Alert Sent!")
                    send_email_alert(f"{symbol} Price Surge 🚀", f"{symbol} increased by ${delta:.2f} to ${current:.2f}")
                elif delta < -2:
                    st.error("📉 Price Drop Alert Sent!")
                    send_email_alert(f"{symbol} Price Drop ⚠️", f"{symbol} dropped by ${delta:.2f} to ${current:.2f}")
                else:
                    st.info("✅ Stable. No alert sent.")

                # Volume Chart
                fig_vol = go.Figure(go.Bar(x=data['Date'], y=data['Volume'], name='Volume', marker_color='teal'))
                fig_vol.update_layout(height=200, margin=dict(t=20))
                st.subheader("📦 Trading Volume")
                st.plotly_chart(fig_vol, use_container_width=True)

                # Logging
                log_file = Path("stock_trend_log.csv")
                new_row = pd.DataFrame([{
                    "Symbol": symbol.upper(),
                    "Time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "Price": current,
                    "Change": delta
                }])
                if log_file.exists():
                    new_row.to_csv(log_file, mode='a', header=False, index=False)
                else:
                    new_row.to_csv(log_file, index=False)

            except Exception as e:
                st.error(f"⚠️ Error with metric or alerts: {e}")

        # --- Company Info ---
        if show_info:
            st.subheader("📄 Company Details")
            ticker = yf.Ticker(symbol)
            try:
                info = ticker.info
                st.write(f"**Name:** {info.get('longName', 'N/A')}")
                st.write(f"**Sector:** {info.get('sector', 'N/A')}")
                st.write(f"**Market Cap:** {info.get('marketCap', 'N/A')}")
                st.write(f"**52 Week High / Low:** {info.get('fiftyTwoWeekHigh', 'N/A')} / {info.get('fiftyTwoWeekLow', 'N/A')}")
                st.write(f"**Summary:** {info.get('longBusinessSummary', 'N/A')}")
            except Exception as e:
                st.warning("⚠️ Company info unavailable.")





