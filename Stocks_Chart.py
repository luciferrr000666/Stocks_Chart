import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta import volatility, momentum, trend
from datetime import datetime
from io import BytesIO
import plotly.graph_objects as go

# Function to calculate technical indicators
def calculate_indicators(data):
    if len(data) < 20:
        return data  # Ensure enough data is present

    # Moving averages
    data['MA_20'] = data['Close'].rolling(window=20).mean()

    # Bollinger Bands
    bb = volatility.BollingerBands(data['Close'], window=20)
    data['BB_Upper'] = bb.bollinger_hband()
    data['BB_Lower'] = bb.bollinger_lband()
    data['BB_Width'] = bb.bollinger_wband()

    # RSI
    rsi = momentum.RSIIndicator(data['Close'], window=14)
    data['RSI'] = rsi.rsi()

    # MACD
    macd = trend.MACD(data['Close'])
    data['MACD_Line'] = macd.macd()
    data['MACD_Signal'] = macd.macd_signal()
    data['MACD_Histogram'] = macd.macd_diff()

    # ADX
    adx = trend.ADXIndicator(data['High'], data['Low'], data['Close'], window=14)
    data['ADX'] = adx.adx()

    return data

# Function to fetch and process stock data for a single ticker
def fetch_stock_data(ticker, start_date, end_date):
    ticker = ticker + ".NS"
    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval='1wk')
        if not data.empty:
            # Ensure data columns are flattened and properly named
            data.reset_index(inplace=True)
            data.columns = data.columns.get_level_values(0)  # Handle MultiIndex if present
            data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            data.set_index('Date', inplace=True)

            # Process and calculate indicators
            data = calculate_indicators(data)
        return data
    except Exception as e:
        st.warning(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

# Function to create candlestick chart
def plot_candlestick_chart(data, ticker):
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=ticker
    )])

    # Add Bollinger Bands to the chart
    if 'BB_Upper' in data.columns and 'BB_Lower' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Upper'],
            mode='lines',
            name='BB Upper',
            line=dict(color='green', width=1, dash='dot')
        ))
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Lower'],
            mode='lines',
            name='BB Lower',
            line=dict(color='red', width=1, dash='dot')
        ))

    # Add moving average to the chart
    if 'MA_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA_20'],
            mode='lines',
            name='MA 20',
            line=dict(color='blue', width=1)
        ))

    # Customize layout
    fig.update_layout(
        title=f"Candlestick Chart for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )

    return fig

# Streamlit app
def main():
    st.title("Stock Performance and Technical Indicators Analyzer")

    # Sidebar options
    st.sidebar.header("Options")
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
    start_date = st.sidebar.date_input("Select Start Date", value=datetime(2023, 1, 1))
    end_date = st.sidebar.date_input("Select End Date", value=datetime(2023, 12, 31))
    save_filename = st.sidebar.text_input("Enter filename to save results (e.g., results.xlsx)", value="stock_analysis.xlsx")

    if uploaded_file:
        # Read the uploaded CSV file
        tickers_df = pd.read_csv(uploaded_file)

        if 'Ticker' not in tickers_df.columns:
            st.error("The uploaded CSV must contain a column named 'Ticker'.")
        else:
            tickers = tickers_df['Ticker'].dropna().unique()
            st.write(f"Found {len(tickers)} tickers to process.")

            aggregated_data = []  # Store the latest data for each ticker

            # Process each ticker
            for ticker in tickers:
                st.write(f"Processing {ticker}...")
                stock_data = fetch_stock_data(ticker, start_date, end_date)

                if not stock_data.empty:
                    # Append the most recent data for aggregation
                    latest_row = stock_data.iloc[-1]
                    latest_row['Date'] = stock_data.index[-1].strftime("%Y-%m-%d")
                    latest_row['Ticker'] = ticker
                    aggregated_data.append(latest_row)

                    # Plot candlestick chart
                    st.plotly_chart(plot_candlestick_chart(stock_data, ticker))
                else:
                    st.warning(f"No data found for {ticker}.")

            if aggregated_data:
                # Save aggregated results to Excel
                aggregated_df = pd.DataFrame(aggregated_data)
                aggregated_df = aggregated_df.reset_index(drop=True)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    aggregated_df.to_excel(writer, sheet_name="Aggregated Results", index=False)

                # Create a download button
                st.download_button(
                    label="Download Excel File",
                    data=output.getvalue(),
                    file_name=save_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("Analysis complete. Download your file using the button above.")

if __name__ == "__main__":
    main()
