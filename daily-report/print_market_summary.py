#!/usr/bin/env python3
"""
輸出 market_data.json 的精簡摘要，供 Claude routine 使用。
避免直接 Read 原始 JSON（超過 2000 行會截斷）。
"""
import json, sys

f = "market_data.json"
d = json.load(open(f, encoding="utf-8"))

def row(name, v):
    if not isinstance(v, dict): return
    c = v.get("last_close"); ch = v.get("change_pct"); rsi = v.get("rsi14")
    ma20 = v.get("ma20"); ma60 = v.get("ma60"); vol = v.get("volume")
    print(f"  {name}: close={c} chg%={ch} rsi={rsi} ma20={ma20} ma60={ma60} vol={vol}")

print(f"=== 生成時間: {d.get('date','')} {d.get('generated_at','')} ===\n")

print("【持倉數據】")
for sym, v in d.get("my_portfolio", {}).items():
    row(sym, v.get("price_data", {}))
    fund = v.get("fundamentals", {})
    if fund and not fund.get("error"):
        pe = fund.get("pe_ratio"); fpe = fund.get("forward_pe")
        eps = fund.get("eps_ttm"); target = fund.get("analyst_target")
        low = fund.get("analyst_low"); high = fund.get("analyst_high")
        rec = fund.get("recommendation"); cap = fund.get("market_cap")
        print(f"    基本面: PE={pe} ForwardPE={fpe} EPS={eps} 目標價={target}({low}~{high}) 評級={rec} 市值={cap}")

print("\n【美股指數】")
for name in ["sp500","nasdaq","dow","russell","sox","vix"]:
    row(name, d["us_markets"].get(name, {}))

print("\n【台股大盤】")
row("taiex", d["tw_markets"].get("taiex", {}))

print("\n【台股個股（有收盤價）】")
for k, v in d["tw_markets"].items():
    if isinstance(v, dict) and v.get("last_close") and \
       not k.endswith(("_institutional", "_margin")) and k != "taiex":
        name = v.get("name", k)
        ch = v.get("change_pct"); rsi = v.get("rsi14"); ma20 = v.get("ma20")
        inst_key = k + "_institutional"
        inst = d["tw_markets"].get(inst_key, {})
        foreign = inst.get("foreign_net"); invest = inst.get("invest_net")
        print(f"  {k} {name}: close={v.get('last_close')} chg%={ch} rsi={rsi} ma20={ma20} 外資={foreign} 投信={invest}")

print("\n【匯率】")
for name, v in d.get("currencies", {}).items():
    row(name, v)

print("\n【公債殖利率】")
for name, v in d.get("bonds", {}).items():
    row(name, v)

print("\n【商品】")
for name, v in d.get("commodities", {}).items():
    row(name, v)
