"""
fetch_securities.py
拉取长桥支持的夜盘标的清单（US/HK/CN），输出到 data/securities.json。

为什么只拉夜盘？
- 长桥 longport 3.0.7 SDK 中 SecurityListCategory 枚举只暴露 Overnight 一个变体，
  底层 Rust 实现也只有 Overnight（其他 Category 在 SDK 编译时未导出）。
- 也就是说，通过长桥无法拿到全市场普通股票清单（A股/港股/美股全量）。
- 夜盘是长桥主打的可交易时段覆盖（美股盘前/盘中/盘后 + 港股夜盘），所以覆盖范围已足够实用。
- 对于夜盘外的任意 ticker，data/symbols.json 仍可手动添加（前端"手动输入 ticker" tab），
  最终在 index.html 中通过 static_info 验证并展示。

输出格式（data/securities.json）：
[
  {
    "symbol": "AAPL.US",          // 长桥标准 ticker（含 .US/.HK/.CN 后缀）
    "name_cn": "苹果",             // 中文名（可能为空）
    "name_en": "Apple Inc.",       // 英文名
    "name_hk": "蘋果",             // 繁体名（可能为空）
    "market": "US"                 // 推断的市场标签：US/HK/CN
  },
  ...
]
"""
import json
import os
import sys
from pathlib import Path

from longport.openapi import (
    Config,
    Market,
    QuoteContext,
    SecurityListCategory,
)


def load_config() -> Config:
    """从环境变量加载长桥凭证。"""
    return Config(
        app_key=os.environ["LONGPORT_APP_KEY"],
        app_secret=os.environ["LONGPORT_APP_SECRET"],
        access_token=os.environ["LONGPORT_ACCESS_TOKEN"],
    )


def infer_market(symbol: str) -> str:
    """根据长桥 ticker 后缀推断市场标签。"""
    if symbol.endswith(".US"):
        return "US"
    if symbol.endswith(".HK"):
        return "HK"
    if symbol.endswith(".CN"):
        return "CN"
    return "UNKNOWN"


def fetch_overnight(ctx: QuoteContext, market: Market) -> list[dict]:
    """拉取单个市场的夜盘清单。"""
    try:
        securities = ctx.security_list(market, SecurityListCategory.Overnight)
    except Exception as e:
        print(f"  [warn] {market.name} 夜盘清单拉取失败：{e}", file=sys.stderr)
        return []

    items = []
    for s in securities:
        symbol = s.symbol
        items.append({
            "symbol": symbol,
            "name_cn": s.name_cn or "",
            "name_en": s.name_en or "",
            "name_hk": s.name_hk or "",
            "market": infer_market(symbol),
        })
    return items


def main() -> int:
    out_path = Path(__file__).resolve().parent.parent / "data" / "securities.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    ctx = QuoteContext(cfg)

    all_items: list[dict] = []
    for market in (Market.US, Market.HK, Market.CN):
        print(f"[fetch] 拉取 {market.name} 夜盘清单...")
        items = fetch_overnight(ctx, market)
        print(f"  -> {len(items)} 个")
        all_items.extend(items)

    # 去重（symbol 唯一）
    seen = set()
    deduped = []
    for item in all_items:
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        deduped.append(item)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"[ok] 共 {len(deduped)} 个夜盘标的 -> {out_path}")
    return 0


# 401004 专项诊断：捕获错误并打印 trace_id/code/body
import traceback as _tb
_diag_trace = []


def _catch_exc(e, prefix: str = "  "):
    print(f"{prefix}type:   {type(e).__module__}.{type(e).__name__}")
    print(f"{prefix}message: {e}")
    try:
        print(f"{prefix}__dict__: {e.__dict__}")
    except Exception:
        pass
    for attr in ("code", "trace_id", "traceId", "msg", "message",
                 "status", "http_status", "body", "raw"):
        if hasattr(e, attr):
            v = getattr(e, attr)
            if v:
                print(f"{prefix}e.{attr} = {v!r}")
    return None


if __name__ == "__main__":
    # 重写 main，加 try/except 打印 401004 详细信息
    out_path = Path(__file__).resolve().parent.parent / "data" / "securities.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    try:
        ctx = QuoteContext(cfg)
    except Exception as e:
        print(f"\n[diag] QuoteContext 构造失败 ❌")
        _catch_exc(e)
        print("\n[diag] traceback:")
        _tb.print_exc()
        sys.exit(1)

    all_items: list[dict] = []
    for market in (Market.US, Market.HK, Market.CN):
        print(f"[fetch] 拉取 {market.name} 夜盘清单...")
        try:
            items = fetch_overnight(ctx, market)
        except Exception as e:
            print(f"  [err] {market.name} ❌")
            _catch_exc(e, prefix="    ")
            items = []
        print(f"  -> {len(items)} 个")
        all_items.extend(items)

    seen = set()
    deduped = []
    for item in all_items:
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        deduped.append(item)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"[ok] 共 {len(deduped)} 个夜盘标的 -> {out_path}")
    sys.exit(0)
