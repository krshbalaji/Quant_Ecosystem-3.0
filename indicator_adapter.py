# indicator_adapter.py

import yfinance as yf
import pandas as pd

class IndicatorAdapter:

    def get_price(self, symbol):
        try:
            ticker = "^NSEI" if symbol == "NIFTY" else symbol
            return float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        except:
            return 0.0

    def get_sma(self, symbol, period=20):
        try:
            ticker = "^NSEI" if symbol == "NIFTY" else symbol
            df = yf.Ticker(ticker).history(period="30d")
            return float(df["Close"].rolling(period).mean().iloc[-1])
        except:
            return 0.0

    def get_rsi(self, symbol, period=14):
        try:
            ticker = "^NSEI" if symbol == "NIFTY" else symbol
            df = yf.Ticker(ticker).history(period="30d")

            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi.iloc[-1])
        except:
            return 50.0

    def get_atr(self, symbol):
        try:
            ticker = "^NSEI" if symbol == "NIFTY" else symbol
            df = yf.Ticker(ticker).history(period="5d")

            high = df["High"]
            low = df["Low"]

            atr = (high - low).rolling(3).mean()
            return float(atr.iloc[-1])
        except:
            return 100.0