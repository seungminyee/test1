# ============================================================
# 매크로 투자 시뮬레이터 MVP - 프로젝트 가이드
# ============================================================
# 
# 이 파일은 MVP를 만들기 위한 전체 로드맵입니다.
# 파이썬 기초(for, if, dict, list)만 알면 됩니다.
#
# 예상 소요시간: 2~3주 (하루 2~3시간 기준)
#   1주차: 데이터 수집 스크립트 완성
#   2주차: Streamlit UI 만들기
#   3주차: 다듬기 + 배포
#
# ============================================================

# ============================================================
# STEP 0. 환경 세팅 (터미널에서 실행)
# ============================================================
"""
pip install yfinance pandas requests streamlit plotly

# 선택사항 (나중에 추가해도 됨)
pip install opendartreader  # DART 실적 데이터
pip install fredapi         # 미국 경제지표
"""

# ============================================================
# STEP 1. 데이터 수집 스크립트 (collect_data.py)
# ============================================================
# 이 스크립트를 한번 돌리면 과거 데이터가 JSON으로 저장됩니다.
# 매일 돌릴 필요 없이, 처음에 한번만 실행하면 됩니다.

import json
import os
from datetime import datetime, timedelta

# ── 1-1. 주가 데이터 수집 ──
def collect_stock_prices():
    """
    yfinance로 한국 주요 종목 주가를 가져옵니다.
    .KS = 코스피, .KQ = 코스닥
    """
    import yfinance as yf
    
    # MVP에서 다룰 종목 (원하는 만큼 추가 가능)
    tickers = {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "현대자동차": "005380.KS",
        "LG화학": "051910.KS",
        "셀트리온": "068270.KS",
        "삼성바이오로직스": "207940.KS",
        "기아": "000270.KS",
        "POSCO홀딩스": "005490.KS",
    }
    
    # 코스피 지수도 가져오기
    indices = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
    }
    
    all_data = {}
    
    # 2015년부터 현재까지 (약 10년치)
    for name, ticker in {**tickers, **indices}.items():
        print(f"  수집 중: {name} ({ticker})")
        try:
            df = yf.download(ticker, start="2015-01-01", progress=False)
            # 날짜별로 종가만 딕셔너리로 변환
            prices = {}
            for date, row in df.iterrows():
                date_str = date.strftime("%Y-%m-%d")
                prices[date_str] = {
                    "close": int(row["Close"]),
                    "open": int(row["Open"]),
                    "high": int(row["High"]),
                    "low": int(row["Low"]),
                    "volume": int(row["Volume"]),
                }
            all_data[name] = prices
            print(f"    → {len(prices)}거래일 수집 완료")
        except Exception as e:
            print(f"    → 실패: {e}")
    
    # JSON으로 저장
    os.makedirs("data", exist_ok=True)
    with open("data/stock_prices.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n저장 완료: data/stock_prices.json")
    return all_data


# ── 1-2. 해외 지수 수집 ──
def collect_global_indices():
    """미국 주요 지수 + VIX(공포지수)"""
    import yfinance as yf
    
    indices = {
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "다우존스": "^DJI",
        "VIX": "^VIX",           # ← 공포지수!
        "미국10년국채": "^TNX",   # ← 금리
        "WTI유가": "CL=F",       # ← 유가
        "금": "GC=F",            # ← 금값
        "달러인덱스": "DX-Y.NYB", # ← 달러 강세/약세
    }
    
    all_data = {}
    for name, ticker in indices.items():
        print(f"  수집 중: {name}")
        try:
            df = yf.download(ticker, start="2015-01-01", progress=False)
            prices = {}
            for date, row in df.iterrows():
                prices[date.strftime("%Y-%m-%d")] = round(float(row["Close"]), 2)
            all_data[name] = prices
        except Exception as e:
            print(f"    → 실패: {e}")
    
    with open("data/global_indices.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"저장 완료: data/global_indices.json")


# ── 1-3. 환율 데이터 ──
def collect_exchange_rate():
    """원/달러 환율"""
    import yfinance as yf
    
    print("  수집 중: USD/KRW 환율")
    df = yf.download("KRW=X", start="2015-01-01", progress=False)
    rates = {}
    for date, row in df.iterrows():
        rates[date.strftime("%Y-%m-%d")] = round(float(row["Close"]), 2)
    
    with open("data/exchange_rate.json", "w", encoding="utf-8") as f:
        json.dump(rates, f, ensure_ascii=False, indent=2)
    
    print(f"저장 완료: data/exchange_rate.json ({len(rates)}일)")


# ── 1-4. 공포탐욕지수 (간이 계산) ──
def calculate_fear_greed():
    """
    CNN Fear & Greed Index의 과거 데이터는 API가 없어서,
    VIX 기반으로 간이 공포탐욕지수를 만듭니다.
    
    VIX 12 이하 = 극단적 탐욕 (90~100)
    VIX 15     = 탐욕 (70~80)  
    VIX 20     = 중립 (50)
    VIX 30     = 공포 (25~30)
    VIX 40+    = 극단적 공포 (0~10)
    
    나중에 더 정교하게 만들 수 있지만 MVP에는 이걸로 충분!
    """
    
    # VIX 데이터 로드
    with open("data/global_indices.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    vix_data = data.get("VIX", {})
    
    fear_greed = {}
    for date, vix in vix_data.items():
        if vix <= 12:
            score = 95
            label = "극단적 탐욕"
        elif vix <= 15:
            score = 75
            label = "탐욕"
        elif vix <= 20:
            score = 55
            label = "중립"
        elif vix <= 25:
            score = 40
            label = "약한 공포"
        elif vix <= 30:
            score = 25
            label = "공포"
        elif vix <= 40:
            score = 12
            label = "강한 공포"
        else:
            score = 5
            label = "극단적 공포"
        
        fear_greed[date] = {"score": score, "label": label, "vix": vix}
    
    with open("data/fear_greed.json", "w", encoding="utf-8") as f:
        json.dump(fear_greed, f, ensure_ascii=False, indent=2)
    
    print(f"저장 완료: data/fear_greed.json ({len(fear_greed)}일)")


# ── 1-5. 뉴스 (2단계에서 추가 - 일단 스킵 가능) ──
def collect_news_bigkinds(api_key):
    """
    BigKinds API로 날짜별 주요 뉴스 헤드라인을 가져옵니다.
    https://www.bigkinds.or.kr 에서 API 키 발급 (학술용 무료)
    
    MVP 1단계에서는 스킵해도 됩니다!
    주가 + 지표만으로도 충분히 쓸만해요.
    """
    import requests
    
    # 예시: 특정 날짜의 경제 뉴스 검색
    params = {
        "access_key": api_key,
        "argument": json.dumps({
            "query": "주식 OR 코스피 OR 금리 OR 환율",
            "published_at": {
                "from": "2020-03-19",
                "until": "2020-03-19"
            },
            "category": ["경제"],
            "sort": {"date": "desc"},
            "return_from": 0,
            "return_size": 10,
        })
    }
    
    resp = requests.post(
        "https://tools.kinds.or.kr/search/news",
        json=params
    )
    
    if resp.ok:
        articles = resp.json().get("documents", [])
        headlines = [
            {"title": a["title"], "source": a["provider"], "date": a["published_at"]}
            for a in articles
        ]
        return headlines
    return []


# ============================================================
# STEP 2. 전체 데이터 수집 실행
# ============================================================
def collect_all():
    """이 함수를 한번 실행하면 모든 데이터가 data/ 폴더에 저장됩니다"""
    print("=" * 50)
    print("매크로 시뮬레이터 데이터 수집 시작")
    print("=" * 50)
    
    print("\n[1/4] 한국 주가 데이터 수집...")
    collect_stock_prices()
    
    print("\n[2/4] 해외 지수 + VIX 수집...")
    collect_global_indices()
    
    print("\n[3/4] 환율 데이터 수집...")
    collect_exchange_rate()
    
    print("\n[4/4] 공포탐욕지수 계산...")
    calculate_fear_greed()
    
    print("\n" + "=" * 50)
    print("데이터 수집 완료!")
    print("다음 단계: streamlit run app.py")
    print("=" * 50)


# 이 파일을 직접 실행하면 데이터 수집 시작
if __name__ == "__main__":
    collect_all()
