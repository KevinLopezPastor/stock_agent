"""
Stock retrieval tools using the yfinance API.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def retrieve_realtime_stock_price(ticker: str) -> str:
    """Get the current real-time stock price and key market data for a given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AMZN', 'AAPL', 'GOOGL').

    Returns:
        JSON string with current price, day range, volume, market cap, and other key metrics.
    """
    logger.info(f"Fetching real-time price for {ticker}")
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or "currentPrice" not in info:
            # Fallback: try fast_info
            fast = stock.fast_info
            result = {
                "ticker": ticker.upper(),
                "current_price": getattr(fast, "last_price", None),
                "previous_close": getattr(fast, "previous_close", None),
                "market_cap": getattr(fast, "market_cap", None),
                "currency": getattr(fast, "currency", "USD"),
                "timestamp": datetime.now().isoformat(),
                "source": "yfinance (fast_info)",
            }
        else:
            result = {
                "ticker": ticker.upper(),
                "current_price": info.get("currentPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "volume": info.get("volume"),
                "average_volume": info.get("averageVolume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange"),
                "company_name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "timestamp": datetime.now().isoformat(),
                "source": "yfinance",
            }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching real-time price for {ticker}: {e}")
        return json.dumps({
            "error": f"Failed to fetch real-time price for {ticker}: {str(e)}",
            "ticker": ticker.upper(),
        })


@tool
def retrieve_historical_stock_price(
    ticker: str,
    period: str = "3mo",
    interval: str = "1d",
) -> str:
    """Get historical stock price data (OHLCV) for a given ticker over a specified period.

    Args:
        ticker: Stock ticker symbol (e.g., 'AMZN', 'AAPL', 'GOOGL').
        period: Time period to retrieve. Valid values:
                '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'.
                Default is '3mo'.
        interval: Data interval. Valid values: '1m', '2m', '5m', '15m',
                  '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo'.
                  Default is '1d'.

    Returns:
        JSON string with historical OHLCV data, including date range and summary statistics.
    """
    logger.info(f"Fetching historical data for {ticker} period={period} interval={interval}")
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            return json.dumps({
                "error": f"No historical data found for {ticker} with period={period}",
                "ticker": ticker.upper(),
            })

        # Convert to serializable format
        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        # Summary statistics
        summary = {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "date_range": {
                "start": records[0]["date"],
                "end": records[-1]["date"],
            },
            "total_data_points": len(records),
            "summary": {
                "start_price": records[0]["close"],
                "end_price": records[-1]["close"],
                "high": max(r["high"] for r in records),
                "low": min(r["low"] for r in records),
                "avg_close": round(sum(r["close"] for r in records) / len(records), 2),
                "avg_volume": int(sum(r["volume"] for r in records) / len(records)),
                "price_change": round(records[-1]["close"] - records[0]["close"], 2),
                "price_change_pct": round(
                    ((records[-1]["close"] - records[0]["close"]) / records[0]["close"]) * 100, 2
                ),
            },
            "data": records,
            "source": "yfinance",
        }

        return json.dumps(summary, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        return json.dumps({
            "error": f"Failed to fetch historical data for {ticker}: {str(e)}",
            "ticker": ticker.upper(),
        })
