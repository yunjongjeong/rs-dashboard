#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유니버스 RS 계산기 — 코스피200 + S&P500 + 주요 ETF의 상대강도(RS)를 매일 계산한다.
IGIS 산식 동일: 장기 RS = 3·6·9·12개월 수익률 가중평균(40·20·20·20%),
              단기 RS = 1·2·4주 수익률 가중평균(50·30·20%),
유니버스 내 백분위(1~99) + z점수(코멧 축)로 변환하고 4분면 등급을 부여한다.
출력: data/rs.json   (대시보드가 읽는 파일)
"""
import json, time, sys, argparse, warnings
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import FinanceDataReader as fdr

warnings.simplefilter("ignore")

# ---- RS 가중치 (거래일 기준) ----
LONG_W  = [(63, 0.40), (126, 0.20), (189, 0.20), (252, 0.20)]   # 3·6·9·12개월
SHORT_W = [(5, 0.50), (10, 0.30), (20, 0.20)]                    # 1·2·4주

# ---- 주요 ETF (미국 + 한국) ----
ETF_US = ["SPY","QQQ","DIA","IWM","VTI","VOO","SOXX","SMH","XLK","VGT","XLF","XLE","XLV",
          "XLI","XLY","XLP","XLU","XLB","XLRE","XLC","ARKK","TAN","ICLN","LIT","IBB","XBI",
          "GLD","SLV","USO","TLT","HYG","EEM","EFA","FXI","EWY","EWJ","VNQ","SCHD","JEPI"]
ETF_KR = ["069500","229200","305540","091160","091170","305720","364980","371460","148020",
          "117460","139260","102110","233740","251340","294400","357870","456600","473460"]

def build_universe(limit=None):
    uni = []
    # 1) 코스피 시총 상위 200
    try:
        k = fdr.StockListing("KOSPI")
        mc = next((c for c in ["Marcap","MarketCap","Amount"] if c in k.columns), None)
        if mc: k = k.sort_values(mc, ascending=False)
        code_col = "Code" if "Code" in k.columns else k.columns[0]
        name_col = "Name" if "Name" in k.columns else k.columns[1]
        for _, r in k.head(200).iterrows():
            uni.append((str(r[code_col]).zfill(6), str(r[name_col]), "한국"))
        print(f"[universe] KOSPI200: {len(uni)}")
    except Exception as e:
        print("[universe] KOSPI 실패:", e)
    # 2) S&P500 — 안정적인 GitHub CSV 우선, 실패 시 FDR
    n0 = len(uni)
    try:
        import requests, io
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        txt = requests.get(url, timeout=20).text
        sp = pd.read_csv(io.StringIO(txt))
        for _, r in sp.iterrows():
            uni.append((str(r["Symbol"]).strip(), str(r.get("Security", r["Symbol"])), "미국"))
        print(f"[universe] S&P500(CSV): {len(uni)-n0}")
    except Exception as e1:
        print("[universe] S&P500 CSV 실패, FDR 시도:", e1)
        try:
            s = fdr.StockListing("S&P500")
            sym = next((c for c in ["Symbol","Code"] if c in s.columns), s.columns[0])
            nm  = next((c for c in ["Name"] if c in s.columns), s.columns[1])
            for _, r in s.iterrows():
                uni.append((str(r[sym]).strip(), str(r[nm]), "미국"))
            print(f"[universe] S&P500(FDR): {len(uni)-n0}")
        except Exception as e2:
            print("[universe] S&P500 실패:", e2)
    # 3) ETF
    for t in ETF_US: uni.append((t, t, "ETF"))
    for t in ETF_KR: uni.append((t, t, "ETF"))
    # dedup
    seen, out = set(), []
    for c, n, m in uni:
        if c in seen: continue
        seen.add(c); out.append((c, n, m))
    if limit: out = out[:limit]
    print(f"[universe] 총 {len(out)} 종목")
    return out

def weighted_return(close, weights):
    if close is None or len(close) < 25:
        return np.nan
    last = float(close.iloc[-1])
    if last <= 0: return np.nan
    acc, wsum = 0.0, 0.0
    for days, w in weights:
        if len(close) > days:
            past = float(close.iloc[-1 - days])
            if past > 0:
                acc += w * (last / past - 1.0); wsum += w
    return acc / wsum if wsum > 0 else np.nan

def fetch_close(code, start):
    for attempt in range(2):
        try:
            df = fdr.DataReader(code, start)
            if df is None or df.empty: return None
            col = "Close" if "Close" in df.columns else df.columns[-1]
            return df[col].dropna()
        except Exception:
            time.sleep(0.6)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="테스트용 종목 수 제한")
    ap.add_argument("--out", default="data/rs.json")
    args = ap.parse_args()

    start = (datetime.now() - timedelta(days=420)).strftime("%Y-%m-%d")
    uni = build_universe(args.limit)

    recs = []
    ok = fail = 0
    for i, (code, name, market) in enumerate(uni, 1):
        close = fetch_close(code, start)
        rl = weighted_return(close, LONG_W)
        rs_ = weighted_return(close, SHORT_W)
        if np.isnan(rl) or np.isnan(rs_):
            fail += 1
        else:
            ok += 1
            recs.append({"code": code, "name": name, "market": market,
                         "rawLong": rl, "rawShort": rs_})
        if i % 100 == 0:
            print(f"  ...{i}/{len(uni)}  (ok {ok} / fail {fail})")
        time.sleep(0.05)  # 예의상 throttle

    if not recs:
        print("[error] 가격을 가져온 종목이 없습니다."); sys.exit(1)

    df = pd.DataFrame(recs)
    # 백분위(1~99)와 z점수(코멧 축, 보기 좋게 *10 스케일)
    df["longRS"]  = (df["rawLong"].rank(pct=True) * 98 + 1).round().astype(int)
    df["shortRS"] = (df["rawShort"].rank(pct=True) * 98 + 1).round().astype(int)
    def zscale(s): 
        sd = s.std(ddof=0) or 1.0
        return ((s - s.mean()) / sd * 10).clip(-40, 40)
    df["longZ"]  = zscale(df["rawLong"]).round(1)
    df["shortZ"] = zscale(df["rawShort"]).round(1)
    def cls(r):
        L, S = r["longZ"], r["shortZ"]
        if L >= 0 and S >= 0: return "lead"
        if L < 0 and S >= 0:  return "improv"
        if L >= 0 and S < 0:  return "weak"
        return "lag"
    df["class"] = df.apply(cls, axis=1)

    payload = {
        "updated": datetime.now().isoformat(timespec="minutes"),
        "count": int(len(df)),
        "weights": {"long": LONG_W, "short": SHORT_W},
        "items": df[["code","name","market","longZ","shortZ","longRS","shortRS","class"]]
                   .sort_values(["longRS","shortRS"], ascending=False)
                   .to_dict(orient="records"),
    }
    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    dist = df["class"].value_counts().to_dict()
    print(f"[done] {len(df)} 종목 → {args.out}  (성공 {ok}/실패 {fail})  분면 {dist}")

if __name__ == "__main__":
    main()
