#!/usr/bin/env python3
import argparse
from statistics import mean

import requests


def fetch_klines(symbol: str, interval: str, limit: int = 200):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if not data:
        raise ValueError(f"Нет данных для {symbol} ({interval}).")

    return data


def sma(values, period: int):
    if len(values) < period:
        return None
    return mean(values[-period:])


def get_signals(closes):
    if len(closes) < 30:
        return []

    signals = []
    for i in range(30, len(closes)):
        short = sma(closes[: i + 1], 7)
        long = sma(closes[: i + 1], 30)

        if short is None or long is None:
            signals.append({"index": i, "signal": "HOLD", "price": closes[i]})
            continue

        if short > long:
            signals.append({"index": i, "signal": "BUY", "price": closes[i]})
        elif short < long:
            signals.append({"index": i, "signal": "SELL", "price": closes[i]})
        else:
            signals.append({"index": i, "signal": "HOLD", "price": closes[i]})

    return signals


def run_backtest(closes, capital: float, fee_rate: float = 0.001):
    capital = float(capital)
    position = 0.0
    entry_price = 0.0
    equity = capital
    trades = []

    for item in get_signals(closes):
        price = item["price"]
        signal = item["signal"]

        if signal == "BUY" and position == 0:
            qty = (capital * 0.95) / price
            position = qty
            entry_price = price
            trades.append({"type": "BUY", "price": price, "qty": qty})

        elif signal == "SELL" and position > 0:
            gross = position * price
            fee = gross * fee_rate
            net = gross - fee
            pnl = net - (position * entry_price)
            equity = equity + pnl
            trades.append({"type": "SELL", "price": price, "qty": position, "pnl": pnl})
            position = 0.0
            entry_price = 0.0

    final_value = equity + (position * closes[-1])
    return {
        "final_value": final_value,
        "initial_capital": capital,
        "trades": trades,
        "profit": final_value - capital,
    }


def main():
    parser = argparse.ArgumentParser(description="Простой крипто-трейдинг бот на SMA-стратегии.")
    parser.add_argument("--symbol", default="BTCUSDT", help="Торговая пара Binance, например BTCUSDT")
    parser.add_argument("--interval", default="1h", help="Таймфрейм, например 1h, 4h, 1d")
    parser.add_argument("--limit", type=int, default=200, help="Количество свечей")
    parser.add_argument("--capital", type=float, default=1000.0, help="Начальный капитал")
    parser.add_argument("--fee", type=float, default=0.001, help="Комиссия как доля от 0 до 1")
    args = parser.parse_args()

    try:
        data = fetch_klines(args.symbol, args.interval, args.limit)
        closes = [float(candle[4]) for candle in data]

        latest = closes[-1]
        short = sma(closes, 7)
        long = sma(closes, 30)

        if short is None or long is None:
            raise ValueError("Недостаточно данных для расчёта SMA.")

        if short > long:
            signal = "BUY"
        elif short < long:
            signal = "SELL"
        else:
            signal = "HOLD"

        result = run_backtest(closes, args.capital, args.fee)

        print(f"\nSymbol: {args.symbol}")
        print(f"Interval: {args.interval}")
        print(f"Price: {latest:.2f}")
        print(f"SMA(7): {short:.2f}")
        print(f"SMA(30): {long:.2f}")
        print(f"Signal: {signal}")
        print(f"Initial capital: {args.capital:.2f}")
        print(f"Final value: {result['final_value']:.2f}")
        print(f"Profit: {result['profit']:.2f}")
        print(f"Trades: {len(result['trades'])}")

    except Exception as exc:  # pragma: no cover
        print(f"Ошибка: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
