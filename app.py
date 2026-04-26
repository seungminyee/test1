# ============================================================
# 매크로 투자 시뮬레이터 MVP - Streamlit App
# ============================================================
# 실행: streamlit run app.py
# ============================================================

import streamlit as st
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── 페이지 설정 ──
st.set_page_config(
    page_title="MACROSIM",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 스타일 (토스 스타일 참고: 깔끔, 미니멀, 다크) ──
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; }
    .main-header { 
        font-size: 2rem; font-weight: 900; 
        color: #ef4444; letter-spacing: 4px; 
    }
    .metric-card {
        background: #141414; border: 1px solid #1f1f1f;
        border-radius: 12px; padding: 16px; margin: 4px 0;
    }
    .metric-label { font-size: 0.75rem; color: #666; font-weight: 600; }
    .metric-value { font-size: 1.4rem; font-weight: 800; }
    .positive { color: #22c55e; }
    .negative { color: #ef4444; }
    .neutral { color: #888; }
    .fear-gauge { 
        text-align: center; padding: 20px;
        background: #141414; border-radius: 12px; 
        border: 1px solid #1f1f1f;
    }
    .fear-score { font-size: 3rem; font-weight: 900; }
    .fear-label { font-size: 1rem; margin-top: 4px; }
    .news-item {
        padding: 10px 0; border-bottom: 1px solid #1a1a1a;
        font-size: 0.9rem; color: #ccc;
    }
    .trade-log {
        font-size: 0.8rem; padding: 6px 0;
        border-bottom: 1px solid #141414;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 데이터 로드
# ============================================================
@st.cache_data
def load_data():
    """data/ 폴더에서 JSON 파일들을 로드합니다"""
    data = {}
    
    files = {
        "prices": "data/stock_prices.json",
        "global": "data/global_indices.json",
        "fx": "data/exchange_rate.json",
        "fear_greed": "data/fear_greed.json",
    }
    
    for key, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
        else:
            data[key] = {}
    
    return data


def get_available_dates(data):
    """데이터에 있는 모든 거래일 목록"""
    if "prices" in data and "KOSPI" in data["prices"]:
        dates = sorted(data["prices"]["KOSPI"].keys())
        return dates
    return []


def get_price(data, stock, date):
    """특정 종목의 특정 날짜 가격"""
    try:
        return data["prices"][stock][date]
    except (KeyError, TypeError):
        return None


def get_nearby_date(dates, target, direction="before"):
    """target에 가장 가까운 거래일 찾기"""
    if target in dates:
        return target
    for d in (reversed(dates) if direction == "before" else dates):
        if (direction == "before" and d <= target) or \
           (direction == "after" and d >= target):
            return d
    return dates[0] if dates else None


# ============================================================
# 세션 상태 초기화 (포트폴리오, 현재 날짜 등)
# ============================================================
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.cash = 100_000_000      # 시작 자금 1억
    st.session_state.holdings = {}            # {종목: {qty, avg_price}}
    st.session_state.journal = []             # 거래 기록
    st.session_state.start_date = None        # 시뮬레이션 시작일
    st.session_state.current_idx = 0          # 현재 날짜 인덱스
    st.session_state.is_playing = False       # 시뮬레이션 진행 중?
    st.session_state.initial_cash = 100_000_000


# ============================================================
# 사이드바: 시뮬레이션 설정
# ============================================================
data = load_data()
dates = get_available_dates(data)

# 데이터가 없으면 안내 메시지
if not dates:
    st.markdown('<p class="main-header">MACROSIM</p>', unsafe_allow_html=True)
    st.markdown("### 데이터가 없습니다!")
    st.markdown("""
    먼저 데이터를 수집해주세요:
    ```
    python collect_data.py
    ```
    수집이 완료되면 이 페이지를 새로고침하세요.
    """)
    
    # 데모 모드: 데이터 없이도 UI를 볼 수 있게
    st.markdown("---")
    st.markdown("### 또는 데모 데이터로 체험하기")
    if st.button("🎮 데모 데이터 생성"):
        # 간단한 데모 데이터 생성
        import random
        os.makedirs("data", exist_ok=True)
        
        demo_prices = {}
        demo_stocks = ["삼성전자", "SK하이닉스", "NAVER", "KOSPI"]
        base_prices = {"삼성전자": 55000, "SK하이닉스": 90000, "NAVER": 180000, "KOSPI": 2200}
        
        for stock in demo_stocks:
            prices = {}
            p = base_prices[stock]
            d = datetime(2020, 1, 2)
            while d <= datetime(2020, 12, 30):
                if d.weekday() < 5:  # 평일만
                    change = random.gauss(0, 0.02)
                    p = int(p * (1 + change))
                    date_str = d.strftime("%Y-%m-%d")
                    prices[date_str] = {
                        "close": p, "open": int(p * 0.99),
                        "high": int(p * 1.01), "low": int(p * 0.98),
                        "volume": random.randint(1000000, 50000000)
                    }
                d += timedelta(days=1)
            demo_prices[stock] = prices
        
        with open("data/stock_prices.json", "w", encoding="utf-8") as f:
            json.dump(demo_prices, f, ensure_ascii=False)
        
        # VIX 기반 공포탐욕
        fear = {}
        d = datetime(2020, 1, 2)
        vix = 15
        while d <= datetime(2020, 12, 30):
            if d.weekday() < 5:
                vix = max(10, min(80, vix + random.gauss(0, 3)))
                date_str = d.strftime("%Y-%m-%d")
                if vix < 15: score, label = 80, "탐욕"
                elif vix < 25: score, label = 50, "중립"
                elif vix < 35: score, label = 25, "공포"
                else: score, label = 10, "극단적 공포"
                fear[date_str] = {"score": score, "label": label, "vix": round(vix, 1)}
            d += timedelta(days=1)
        
        with open("data/fear_greed.json", "w", encoding="utf-8") as f:
            json.dump(fear, f, ensure_ascii=False)
        
        # 환율
        fx = {}
        d, rate = datetime(2020, 1, 2), 1160
        while d <= datetime(2020, 12, 30):
            if d.weekday() < 5:
                rate = max(1100, min(1350, rate + random.gauss(0, 5)))
                fx[d.strftime("%Y-%m-%d")] = round(rate, 2)
            d += timedelta(days=1)
        
        with open("data/exchange_rate.json", "w", encoding="utf-8") as f:
            json.dump(fx, f, ensure_ascii=False)
        
        with open("data/global_indices.json", "w", encoding="utf-8") as f:
            json.dump({}, f)
        
        st.success("데모 데이터 생성 완료! 새로고침하세요.")
        st.rerun()
    
    st.stop()


# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("## ⏰ 시뮬레이션 설정")
    
    # 시작 날짜 선택
    min_date = datetime.strptime(dates[0], "%Y-%m-%d")
    max_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    
    start = st.date_input(
        "시작 날짜를 선택하세요",
        value=datetime(2020, 1, 2),
        min_value=min_date,
        max_value=max_date,
    )
    
    start_str = start.strftime("%Y-%m-%d")
    actual_start = get_nearby_date(dates, start_str, "after")
    
    if st.button("🚀 이 날짜에서 시작하기", use_container_width=True):
        st.session_state.start_date = actual_start
        st.session_state.current_idx = dates.index(actual_start)
        st.session_state.cash = 100_000_000
        st.session_state.holdings = {}
        st.session_state.journal = []
        st.session_state.is_playing = True
        st.session_state.initial_cash = 100_000_000
        st.rerun()
    
    st.markdown("---")
    
    # 초기 자금 설정
    st.markdown("### 💰 시작 자금")
    start_cash = st.select_slider(
        "시작 자금",
        options=[10_000_000, 30_000_000, 50_000_000, 100_000_000, 500_000_000],
        value=100_000_000,
        format_func=lambda x: f"{x//10000:,}만원",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 📊 종목 목록")
    stocks = [s for s in data.get("prices", {}).keys() if s not in ["KOSPI", "KOSDAQ"]]
    for s in stocks:
        st.markdown(f"• {s}")


# ============================================================
# 메인 화면
# ============================================================
if not st.session_state.is_playing:
    # 시작 전 화면
    st.markdown('<p class="main-header">MACROSIM</p>', unsafe_allow_html=True)
    st.markdown("#### 과거로 돌아가 투자 판단을 내려보세요")
    st.markdown(f"**{len(dates)}거래일** 데이터 · **{len(stocks)}종목** · "
                f"**{dates[0]}** ~ **{dates[-1]}**")
    st.markdown("")
    st.info("👈 사이드바에서 시작 날짜를 선택하고 '시작하기'를 누르세요")
    st.stop()


# ── 현재 날짜 정보 ──
current_date = dates[st.session_state.current_idx]
prev_date = dates[st.session_state.current_idx - 1] if st.session_state.current_idx > 0 else current_date


# ── 상단: 날짜 + 네비게이션 ──
col_date, col_nav = st.columns([3, 2])
with col_date:
    weekday = datetime.strptime(current_date, "%Y-%m-%d").strftime("%A")
    weekday_kr = {"Monday": "월", "Tuesday": "화", "Wednesday": "수", 
                  "Thursday": "목", "Friday": "금"}
    st.markdown(f"### 📅 {current_date} ({weekday_kr.get(weekday, '')})")

with col_nav:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("◀ 1일", use_container_width=True):
            if st.session_state.current_idx > dates.index(st.session_state.start_date):
                st.session_state.current_idx -= 1
                st.rerun()
    with c2:
        if st.button("1일 ▶", use_container_width=True):
            if st.session_state.current_idx < len(dates) - 1:
                st.session_state.current_idx += 1
                st.rerun()
    with c3:
        if st.button("1주 ▶▶", use_container_width=True):
            st.session_state.current_idx = min(len(dates) - 1, st.session_state.current_idx + 5)
            st.rerun()
    with c4:
        if st.button("1달 ▶▶▶", use_container_width=True):
            st.session_state.current_idx = min(len(dates) - 1, st.session_state.current_idx + 22)
            st.rerun()

st.markdown("---")


# ── 포트폴리오 요약 ──
total_holdings_value = 0
for stock_name, h in st.session_state.holdings.items():
    p = get_price(data, stock_name, current_date)
    if p:
        total_holdings_value += h["qty"] * p["close"]

total_asset = st.session_state.cash + total_holdings_value
total_return = (total_asset - st.session_state.initial_cash) / st.session_state.initial_cash * 100

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    color = "positive" if total_return >= 0 else "negative"
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">총 자산</div>
        <div class="metric-value {color}">{total_asset:,.0f}원</div>
        <div class="{color}">{'+'if total_return>=0 else ''}{total_return:.2f}%</div>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">현금</div>
        <div class="metric-value neutral">{st.session_state.cash:,.0f}원</div>
    </div>""", unsafe_allow_html=True)
with col_c:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">보유종목 평가</div>
        <div class="metric-value neutral">{total_holdings_value:,.0f}원</div>
        <div class="neutral">{len(st.session_state.holdings)}종목 보유</div>
    </div>""", unsafe_allow_html=True)
with col_d:
    # 공포탐욕지수
    fg = data.get("fear_greed", {}).get(current_date, {})
    fg_score = fg.get("score", 50)
    fg_label = fg.get("label", "데이터 없음")
    fg_color = "positive" if fg_score > 60 else ("negative" if fg_score < 40 else "neutral")
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">공포탐욕지수</div>
        <div class="metric-value {fg_color}">{fg_score}</div>
        <div class="{fg_color}">{fg_label}</div>
    </div>""", unsafe_allow_html=True)


# ── 메인 영역: 차트 + 매매 ──
tab_chart, tab_trade, tab_portfolio, tab_indicators = st.tabs(
    ["📈 차트", "💹 매매", "📋 포트폴리오", "🌡️ 시장 지표"]
)

# ── 차트 탭 ──
with tab_chart:
    selected_stock = st.selectbox("종목 선택", stocks + ["KOSPI"])
    
    # 현재 날짜까지의 데이터만 보여주기 (미래 정보 차단!)
    stock_data = data.get("prices", {}).get(selected_stock, {})
    chart_dates = [d for d in sorted(stock_data.keys()) if d <= current_date]
    
    # 최근 60거래일만 표시 (너무 많으면 느려짐)
    chart_dates = chart_dates[-60:]
    
    if chart_dates:
        closes = [stock_data[d]["close"] for d in chart_dates]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_dates, y=closes,
            mode="lines",
            line=dict(
                color="#22c55e" if closes[-1] >= closes[0] else "#ef4444",
                width=2
            ),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.1)" if closes[-1] >= closes[0] else "rgba(239,68,68,0.1)",
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0a0a",
            plot_bgcolor="#0a0a0a",
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#1a1a1a"),
            showlegend=False,
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 현재가 정보
        current_price_data = stock_data.get(current_date, {})
        prev_price_data = stock_data.get(prev_date, {})
        
        if current_price_data:
            cp = current_price_data["close"]
            pp = prev_price_data.get("close", cp)
            change = cp - pp
            change_pct = (change / pp * 100) if pp else 0
            
            c1, c2, c3 = st.columns(3)
            with c1:
                color = "positive" if change >= 0 else "negative"
                st.markdown(f"""**현재가** <span class="{color}">{cp:,}원 
                ({'+'if change>=0 else ''}{change:,} / {change_pct:+.2f}%)</span>""",
                unsafe_allow_html=True)
            with c2:
                st.markdown(f"**거래량** {current_price_data.get('volume', 0):,}")
            with c3:
                st.markdown(f"**시가** {current_price_data.get('open', 0):,} · "
                          f"**고가** {current_price_data.get('high', 0):,} · "
                          f"**저가** {current_price_data.get('low', 0):,}")

# ── 매매 탭 ──
with tab_trade:
    st.markdown("### 주문")
    
    trade_stock = st.selectbox("매매 종목", stocks, key="trade_stock")
    trade_price_data = get_price(data, trade_stock, current_date)
    
    if trade_price_data:
        trade_price = trade_price_data["close"]
        st.markdown(f"**{trade_stock}** 현재가: **{trade_price:,}원**")
        
        max_buy = st.session_state.cash // trade_price
        current_holding = st.session_state.holdings.get(trade_stock, {}).get("qty", 0)
        
        col_buy, col_sell = st.columns(2)
        
        with col_buy:
            st.markdown("#### 매수")
            buy_qty = st.number_input(
                f"수량 (최대 {max_buy:,}주)", 
                min_value=0, max_value=max_buy, value=0,
                key="buy_qty"
            )
            if buy_qty > 0:
                st.markdown(f"총 금액: **{buy_qty * trade_price:,}원**")
            
            if st.button("🔴 매수", use_container_width=True, disabled=buy_qty <= 0):
                cost = buy_qty * trade_price
                h = st.session_state.holdings.get(trade_stock, {"qty": 0, "avg_price": 0})
                new_qty = h["qty"] + buy_qty
                new_avg = (h["avg_price"] * h["qty"] + cost) / new_qty
                st.session_state.holdings[trade_stock] = {"qty": new_qty, "avg_price": new_avg}
                st.session_state.cash -= cost
                st.session_state.journal.append({
                    "date": current_date, "stock": trade_stock,
                    "action": "매수", "qty": buy_qty, "price": trade_price
                })
                st.success(f"{trade_stock} {buy_qty}주 매수 완료!")
                st.rerun()
        
        with col_sell:
            st.markdown("#### 매도")
            sell_qty = st.number_input(
                f"수량 (보유 {current_holding:,}주)",
                min_value=0, max_value=current_holding, value=0,
                key="sell_qty"
            )
            if sell_qty > 0:
                st.markdown(f"매도 금액: **{sell_qty * trade_price:,}원**")
            
            if st.button("🔵 매도", use_container_width=True, disabled=sell_qty <= 0):
                revenue = sell_qty * trade_price
                h = st.session_state.holdings[trade_stock]
                new_qty = h["qty"] - sell_qty
                if new_qty > 0:
                    st.session_state.holdings[trade_stock]["qty"] = new_qty
                else:
                    del st.session_state.holdings[trade_stock]
                st.session_state.cash += revenue
                st.session_state.journal.append({
                    "date": current_date, "stock": trade_stock,
                    "action": "매도", "qty": sell_qty, "price": trade_price
                })
                st.success(f"{trade_stock} {sell_qty}주 매도 완료!")
                st.rerun()

# ── 포트폴리오 탭 ──
with tab_portfolio:
    st.markdown("### 보유 종목")
    
    if not st.session_state.holdings:
        st.info("보유 종목이 없습니다. 매매 탭에서 종목을 매수해보세요.")
    else:
        for stock_name, h in st.session_state.holdings.items():
            p = get_price(data, stock_name, current_date)
            if p:
                current_val = h["qty"] * p["close"]
                pl = (p["close"] - h["avg_price"]) / h["avg_price"] * 100
                color = "positive" if pl >= 0 else "negative"
                
                st.markdown(f"""<div class="metric-card">
                    <b>{stock_name}</b> · {h['qty']:,}주<br>
                    평단가 {h['avg_price']:,.0f}원 → 현재가 {p['close']:,}원<br>
                    평가 <span class="{color}">{current_val:,.0f}원 ({pl:+.2f}%)</span>
                </div>""", unsafe_allow_html=True)
    
    if st.session_state.journal:
        st.markdown("### 거래 기록")
        for j in reversed(st.session_state.journal[-20:]):
            action_color = "🔴" if j["action"] == "매수" else "🔵"
            st.markdown(f"""<div class="trade-log">
                {action_color} {j['date']} · {j['stock']} · {j['action']} 
                · {j['qty']:,}주 × {j['price']:,}원
            </div>""", unsafe_allow_html=True)

# ── 시장 지표 탭 ──
with tab_indicators:
    st.markdown("### 시장 지표")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 공포탐욕지수 게이지
        fg = data.get("fear_greed", {}).get(current_date, {})
        score = fg.get("score", 50)
        label = fg.get("label", "-")
        vix = fg.get("vix", "-")
        
        if score < 25: color = "#ef4444"
        elif score < 45: color = "#f97316"
        elif score < 55: color = "#eab308"
        elif score < 75: color = "#22c55e"
        else: color = "#16a34a"
        
        st.markdown(f"""<div class="fear-gauge">
            <div class="metric-label">공포탐욕지수</div>
            <div class="fear-score" style="color:{color}">{score}</div>
            <div class="fear-label" style="color:{color}">{label}</div>
            <div class="metric-label" style="margin-top:8px">VIX: {vix}</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        # 환율
        fx_rate = data.get("fx", {}).get(current_date, "-")
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">원/달러 환율</div>
            <div class="metric-value">{fx_rate}</div>
        </div>""", unsafe_allow_html=True)
        
        # KOSPI
        kospi = get_price(data, "KOSPI", current_date)
        if kospi:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">KOSPI</div>
                <div class="metric-value">{kospi['close']:,}</div>
            </div>""", unsafe_allow_html=True)
    
    # 최근 공포탐욕 추이
    fg_data = data.get("fear_greed", {})
    fg_dates = [d for d in sorted(fg_data.keys()) if d <= current_date][-30:]
    if fg_dates:
        fg_scores = [fg_data[d]["score"] for d in fg_dates]
        
        fig_fg = go.Figure()
        fig_fg.add_trace(go.Scatter(
            x=fg_dates, y=fg_scores,
            mode="lines+markers",
            line=dict(color="#fbbf24", width=2),
            marker=dict(size=4),
        ))
        fig_fg.add_hline(y=25, line_dash="dash", line_color="#ef4444", opacity=0.5,
                        annotation_text="극단적 공포")
        fig_fg.add_hline(y=75, line_dash="dash", line_color="#22c55e", opacity=0.5,
                        annotation_text="극단적 탐욕")
        fig_fg.update_layout(
            title="공포탐욕지수 30일 추이",
            template="plotly_dark",
            paper_bgcolor="#0a0a0a",
            plot_bgcolor="#0a0a0a",
            height=250,
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#1a1a1a"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_fg, use_container_width=True)
