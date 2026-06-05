"""
fetch_klines.py
按 data/symbols.json 拉取每个标的的 K 线数据，输出到 data/klines.json。

输出结构（按 symbol 索引）：
{
  "AAPL": {
    "symbol": "AAPL.US",
    "name": "苹果",
    "type": "stock",
    "candles": {
      "1d": [ { "timestamp": 1717200000, "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "turnover": ... }, ... ],
      "1h": [...],
      "15m": [...],
      "5m":  [...]
    },
    "static_info": {
      "exchange": "NASDAQ",
      "currency": "USD",
      "lot_size": 1
    },
    "fetched_at": "2026-06-05T21:00:00+08:00"
  },
  ...
}

K 线时间区间（每周期拉取根数）：
- 日 K (1d): 500 根 ≈ 2 年交易日
- 小时 K (1h): 500 根 ≈ 21 天
- 15 分钟 K (15m): 500 根 ≈ 5 天
- 5 分钟 K (5m):  500 根 ≈ 1.7 天

Note: longport SDK Period 枚举的 timespan 字符串为 'day' / 'hour' / 'minute' / 'week' / 'month' / 'quarter' / 'year'。
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from longport.openapi import (
    Config,
    Period,
    AdjustType,
    QuoteContext,
)


# 北京时区
CST = timezone(timedelta(hours=8))


def load_config() -> Config:
    return Config(
        app_key=os.environ["LONGPORT_APP_KEY"],
        app_secret=os.environ["LONGPORT_APP_SECRET"],
        access_token=os.environ["LONGPORT_ACCESS_TOKEN"],
    )


def load_symbols() -> list[dict]:
    """读取 data/symbols.json（数组），过滤 _ 开头注释键。"""
    data_path = Path(__file__).resolve().parent.parent / "data" / "symbols.json"
    if not data_path.exists():
        print(f"[err] 找不到 {data_path}", file=sys.stderr)
        return []
    with data_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    # 过滤 _ 开头的非标的条目
    return [s for s in raw if not str(s.get("ticker", "")).startswith("_")]


# 周期配置：(Period 枚举, 输出键, 拉取根数)
# 注意：longport 3.0.23 的 Period 枚举是 Min_5/Min_15/Min_60/Day（没有 Hour 也没有 Min_30 这种"边界"枚举）
PERIOD_CONFIG = [
    (Period.Day,    "1d",  500),
    (Period.Min_60, "1h",  500),
    (Period.Min_15, "15m", 500),
    (Period.Min_5,  "5m",  500),
]


def fetch_period(ctx: QuoteContext, symbol: str, period: Period, count: int) -> list[dict]:
    """拉取一个周期的一段 K 线。"""
    try:
        candles = ctx.candlesticks(symbol, period, count, AdjustType.NoAdjust)
    except Exception as e:
        print(f"    [warn] {symbol} period={period} 拉取失败：{e}", file=sys.stderr)
        return []
    return [
        {
            "timestamp": int(c.timestamp.timestamp()),
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume) if c.volume is not None else 0.0,
            "turnover": float(c.turnover) if c.turnover is not None else 0.0,
        }
        for c in candles
    ]


def to_longport_symbol(ticker: str) -> str:
    """
    把用户写的 ticker 标准化为长桥格式：
    - 'AAPL'       -> 'AAPL.US'
    - '00700.HK'   -> '00700.HK' (已合规)
    - '600519.SH'  -> '600519.SH' (已合规)
    - 'BTCUSD'     -> 'BTCUSD'    (加密货币)
    - 'TSLA.US'    -> 'TSLA.US'   (已合规)
    """
    t = ticker.strip().upper()
    if "." in t:
        return t
    # 美股：纯字母 → 加 .US
    if t.isalpha() and t.isascii():
        return f"{t}.US"
    return t


def fetch_static_info(ctx: QuoteContext, symbol: str) -> dict[str, Any]:
    """拉取静态信息（交易所/币种/最小交易单位）。失败时返回空 dict。"""
    try:
        infos = ctx.static_info([symbol])
        if not infos:
            return {}
        info = infos[0]
        return {
            "exchange": str(info.exchange) if info.exchange else "",
            "currency": str(info.currency) if info.currency else "",
            "lot_size": int(info.lot_size) if info.lot_size else 0,
        }
    except Exception as e:
        print(f"    [warn] {symbol} static_info 失败：{e}", file=sys.stderr)
        return {}


def main() -> int:
    out_path = Path(__file__).resolve().parent.parent / "data" / "klines.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    ctx = QuoteContext(cfg)

    symbols = load_symbols()
    print(f"[fetch] 共 {len(symbols)} 个标的")

    output: dict[str, Any] = {}
    for sym_obj in symbols:
        user_ticker = sym_obj["ticker"]
        name = sym_obj.get("name", "")
        sym_type = sym_obj.get("type", "stock")
        longport_sym = to_longport_symbol(user_ticker)
        print(f"  - {user_ticker} -> {longport_sym}")

        candles_by_period: dict[str, list[dict]] = {}
        for period, key, count in PERIOD_CONFIG:
            candles_by_period[key] = fetch_period(ctx, longport_sym, period, count)

        static = fetch_static_info(ctx, longport_sym)

        output[user_ticker] = {
            "symbol": longport_sym,
            "name": name,
            "type": sym_type,
            "candles": candles_by_period,
            "static_info": static,
            "fetched_at": datetime.now(CST).isoformat(timespec="seconds"),
        }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[ok] K 线数据 -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
