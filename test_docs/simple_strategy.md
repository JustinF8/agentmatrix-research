# Simple Mean Reversion Strategy

This document outlines a simple mean reversion strategy for trading stocks.

## Concept
The strategy assumes that prices tend to move back to the average price over time. We use Bollinger Bands to identify overbought and oversold conditions.

## Inputs
- Stock Symbol (e.g., AAPL)
- Timeframe (e.g., 1 Day)

## Logic
1. Fetch historical OHLCV data for the given symbol.
2. Calculate the 20-day Simple Moving Average (SMA).
3. Calculate the standard deviation over the last 20 days.
4. Calculate Upper Band = SMA + (2 * StdDev).
5. Calculate Lower Band = SMA - (2 * StdDev).
6. **Buy Signal**: If the closing price crosses below the Lower Band.
7. **Sell Signal**: If the closing price crosses above the Upper Band.
8. **Hold**: Otherwise.

## Output
- A signal: "BUY", "SELL", or "HOLD".
