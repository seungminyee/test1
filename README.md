# MACROSIM - 매크로 투자 시뮬레이터 MVP

과거로 돌아가 투자 판단을 내려보는 시뮬레이터.
실제 주가/지표 데이터 기반, 미래 정보 차단.

## 빠른 시작 (10분)

### 1. 설치
```bash
pip install yfinance pandas requests streamlit plotly
```

### 2. 데이터 수집
```bash
python collect_data.py
```
첫 실행 시 5~10분 소요. 이후 다시 실행할 필요 없음.

### 3. 실행
```bash
streamlit run app.py
```
브라우저에서 자동으로 열립니다.

## 파일 구조
```
macro-sim-mvp/
├── collect_data.py    # 데이터 수집 스크립트
├── app.py             # Streamlit 앱 (메인)
├── README.md          # 이 파일
└── data/              # 수집된 데이터 (자동 생성)
    ├── stock_prices.json
    ├── global_indices.json
    ├── exchange_rate.json
    └── fear_greed.json
```

## 포함된 데이터

| 데이터 | 소스 | 비용 |
|--------|------|------|
| 한국 주요 종목 주가 | Yahoo Finance | 무료 |
| KOSPI/KOSDAQ 지수 | Yahoo Finance | 무료 |
| S&P500, NASDAQ, 다우 | Yahoo Finance | 무료 |
| VIX (공포지수) | Yahoo Finance | 무료 |
| 원/달러 환율 | Yahoo Finance | 무료 |
| WTI 유가, 금값 | Yahoo Finance | 무료 |
| 공포탐욕지수 (간이) | VIX 기반 계산 | 무료 |

## 다음 단계 (추가하고 싶을 때)

### 뉴스 추가
BigKinds API 키 발급 → collect_data.py의 collect_news_bigkinds() 활성화

### 실적 데이터 추가
```bash
pip install opendartreader
```
DART API 키 발급 (https://opendart.fss.or.kr) → 실적 수집 함수 추가

### 종목 추가
collect_data.py의 tickers 딕셔너리에 종목 추가하고 다시 실행

### 배포 (무료)
```bash
# Streamlit Cloud (가장 쉬움)
# 1. GitHub에 push
# 2. https://streamlit.io/cloud 에서 연결
# 끝!
```
