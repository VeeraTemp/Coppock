import time
import yfinance as yf
import pandas as pd
import os
from functools import lru_cache
from datetime import datetime, timedelta
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, filename='etf_tracker.log')
logger = logging.getLogger(__name__)

# Full ETF list
ETF_SYMBOLS = [
    "LIQUIDBEES.NS", "GROWWLIQID.NS", "HDFCLIQUID.NS", "LIQUIDETF.NS", "LIQUIDIETF.NS", "LIQUIDPLUS.NS",
    "LIQUIDSBI.NS", "LIQUIDSHRI.NS", "ALPHAETF.NS", "ALPL30IETF.NS", "AUTOBEES.NS", "AUTOIETF.NS", "AXISGOLD.NS",
    "BANKBEES.NS", "BANKIETF.NS", "CONSUMBEES.NS", "CPSEETF.NS", "EBBETF0430.NS", "EBBETF0431.NS", "EBBETF0433.NS",
    "FMCGIETF.NS", "GOLD1.NS", "GOLDBEES.NS", "GOLDIETF.NS", "GOLDSHARE.NS", "GROWWGOLD.NS", "HDFCGOLD.NS",
    "HDFCSILVER.NS", "HDFCSML250.NS", "ICICIB22.NS", "ITBEES.NS", "ITIETF.NS", "JUNIORBEES.NS", "LOWVOLIETF.NS",
    "MID150BEES.NS", "MOM30IETF.NS", "NEXT50IETF.NS", "NIFTYBEES.NS", "NIFTYIETF.NS", "NV20IETF.NS", "PHARMABEES.NS",
    "PSUBNKBEES.NS", "PVTBANIETF.NS", "SETFGOLD.NS", "SETFNIF50.NS", "SILVER.NS", "SILVERBEES.NS", "SILVERETF.NS",
    "SILVERIETF.NS", "TATAGOLD.NS", "MAFANG.NS", "MOM100.NS", "MON100.NS", "NIFTYETF.NS", "SETFNIFBK.NS",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "INFY.NS", "ITC.NS", "SBIN.NS",
    "BHARTIARTL.NS", "LICI.NS",
    "LT.NS", "KOTAKBANK.NS", "HCLTECH.NS", "ASIANPAINT.NS", "DMART.NS", "BAJFINANCE.NS", "WIPRO.NS", "ADANIENT.NS",
    "ONGC.NS", "TITAN.NS",
    "NTPC.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "BAJAJFINSV.NS", "POWERGRID.NS", "ADANIPORTS.NS", "COALINDIA.NS",
    "TATASTEEL.NS", "JSWSTEEL.NS",
    "ADANIGREEN.NS", "HDFCLIFE.NS", "IOC.NS", "SUNPHARMA.NS", "AXISBANK.NS", "TECHM.NS", "GRASIM.NS", "SBILIFE.NS",
    "BRITANNIA.NS", "M&M.NS",
    "INDUSINDBK.NS", "CIPLA.NS", "HINDALCO.NS", "DIVISLAB.NS", "BPCL.NS", "TATAMOTORS.NS", "HEROMOTOCO.NS",
    "EICHERMOT.NS", "DRREDDY.NS", "UPL.NS"
]


class ETFTracker:
    def __init__(self):
        self.ETF_SYMBOLS = ETF_SYMBOLS

    @lru_cache(maxsize=128)
    def _get_etf_history(self, symbol, period="1y", interval="1d"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return None
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {str(e)}")
            return None

    def _weighted_moving_average(self, series, window):
        weights = np.arange(1, window + 1)
        return series.rolling(window).apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw=True)

    def _calculate_coppock(self, close_prices, w1=11, w2=14, wma=10):
        roc1 = close_prices.pct_change(periods=w1)
        roc2 = close_prices.pct_change(periods=w2)
        coppock_raw = roc1 + roc2
        return self._weighted_moving_average(coppock_raw, wma)

    def _calculate_macd(self, close_prices, fast=8, slow=21, signal=5):
        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line

    def get_crosses(self):
        signals = []
        for symbol in self.ETF_SYMBOLS:
            try:
                df = self._get_etf_history(symbol)
                if df is None or df.empty or len(df) < 100:
                    continue

                # Calculate indicators
                df['Coppock'] = self._calculate_coppock(df['Close'])
                macd_line, signal_line = self._calculate_macd(df['Close'])
                df['MACD_Line'] = macd_line
                df['MACD_Signal'] = signal_line
                df = df.dropna()

                if len(df) < 2:
                    continue

                # Check for crosses
                last_coppock, prev_coppock = df['Coppock'].iloc[-1], df['Coppock'].iloc[-2]
                last_macd_line, prev_macd_line = df['MACD_Line'].iloc[-1], df['MACD_Line'].iloc[-2]
                last_macd_signal, prev_macd_signal = df['MACD_Signal'].iloc[-1], df['MACD_Signal'].iloc[-2]

                # Coppock signals
                if prev_coppock < 0 and last_coppock > 0:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'Coppock',
                        'type': 'bullish',
                        'value': last_coppock,
                        'crossover': 'zero'
                    })
                elif prev_coppock > 0 and last_coppock < 0:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'Coppock',
                        'type': 'bearish',
                        'value': last_coppock,
                        'crossover': 'zero'
                    })

                # MACD line crossing zero
                if prev_macd_line < 0 and last_macd_line > 0:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'MACD',
                        'type': 'bullish',
                        'value': last_macd_line,
                        'crossover': 'zero'
                    })
                elif prev_macd_line > 0 and last_macd_line < 0:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'MACD',
                        'type': 'bearish',
                        'value': last_macd_line,
                        'crossover': 'zero'
                    })

                # MACD line crossing signal line
                if prev_macd_line < prev_macd_signal and last_macd_line > last_macd_signal:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'MACD',
                        'type': 'bullish',
                        'value': last_macd_line - last_macd_signal,
                        'crossover': 'signal'
                    })
                elif prev_macd_line > prev_macd_signal and last_macd_line < last_macd_signal:
                    signals.append({
                        'symbol': symbol,
                        'indicator': 'MACD',
                        'type': 'bearish',
                        'value': last_macd_line - last_macd_signal,
                        'crossover': 'signal'
                    })

            except Exception as e:
                logger.error(f"Error calculating indicators for {symbol}: {str(e)}")
                continue
        return signals

    def get_historical_crosses(self, lookback_days):
        signals = []
        for symbol in self.ETF_SYMBOLS:
            try:
                df = self._get_etf_history(symbol, period=f"{lookback_days + 50}d")
                if df is None or df.empty or len(df) < lookback_days:
                    continue

                # Calculate indicators
                df['Coppock'] = self._calculate_coppock(df['Close'])
                macd_line, signal_line = self._calculate_macd(df['Close'])
                df['MACD_Line'] = macd_line
                df['MACD_Signal'] = signal_line
                df = df.dropna()

                for i in range(-lookback_days, 0):
                    if i - 1 < -len(df):
                        continue

                    date = df.index[i].strftime('%Y-%m-%d')
                    prev_coppock, curr_coppock = df['Coppock'].iloc[i - 1], df['Coppock'].iloc[i]
                    prev_macd_line, curr_macd_line = df['MACD_Line'].iloc[i - 1], df['MACD_Line'].iloc[i]
                    prev_macd_signal, curr_macd_signal = df['MACD_Signal'].iloc[i - 1], df['MACD_Signal'].iloc[i]

                    # Coppock signals
                    if prev_coppock < 0 and curr_coppock > 0:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'Coppock',
                            'type': 'bullish',
                            'value': curr_coppock,
                            'crossover': 'zero'
                        })
                    elif prev_coppock > 0 and curr_coppock < 0:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'Coppock',
                            'type': 'bearish',
                            'value': curr_coppock,
                            'crossover': 'zero'
                        })

                    # MACD line crossing zero
                    if prev_macd_line < 0 and curr_macd_line > 0:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'MACD',
                            'type': 'bullish',
                            'value': curr_macd_line,
                            'crossover': 'zero'
                        })
                    elif prev_macd_line > 0 and curr_macd_line < 0:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'MACD',
                            'type': 'bearish',
                            'value': curr_macd_line,
                            'crossover': 'zero'
                        })

                    # MACD line crossing signal line
                    if prev_macd_line < prev_macd_signal and curr_macd_line > curr_macd_signal:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'MACD',
                            'type': 'bullish',
                            'value': curr_macd_line - curr_macd_signal,
                            'crossover': 'signal'
                        })
                    elif prev_macd_line > prev_macd_signal and curr_macd_line < curr_macd_signal:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'indicator': 'MACD',
                            'type': 'bearish',
                            'value': curr_macd_line - curr_macd_signal,
                            'crossover': 'signal'
                        })

            except Exception as e:
                logger.error(f"Error processing {symbol} for historical data: {str(e)}")
                continue

        # Convert to DataFrame for easier manipulation
        return pd.DataFrame(signals)


def display_menu():
    print("\n\U0001F4CB ETF Tracker Menu:")
    print("11. Show ETFs with indicator crossovers")
    print("12. Show historical crossovers (lookback)")
    print("0. Exit")


def main():
    tracker = ETFTracker()

    while True:
        display_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "0":
            print("Exiting ETF Tracker. Goodbye!")
            break

        elif choice == "11":
            signals = tracker.get_crosses()
            print("\n\U0001F4CA Indicator Cross Alerts:")
            if signals:
                df = pd.DataFrame(signals)
                print(df.to_string(index=False))
            else:
                print("No crossover signals today.")

        elif choice == "12":
            try:
                days = int(input("Enter number of past days to look back: "))
                results = tracker.get_historical_crosses(days)
                print("\n\U0001F570️ Historical Crossovers:")
                if results.empty:
                    print("No crossover signals in the given period.")
                else:
                    print(results.to_string(index=False))
            except ValueError:
                print("❌ Invalid number of days. Please enter a valid integer.")

        else:
            print("❌ Invalid choice. Please select a valid option.")


if __name__ == "__main__":
    main()