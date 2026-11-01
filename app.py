import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# 1. 페이지 설정 및 기본 레이아웃 지정
st.set_page_config(
    page_title="스마트 전력 사용 및 탄소 배출량 이동 시뮬레이터",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 커스텀 CSS (미감 살리기: 고급 에코 그린 톤, 카드 섀도우, 깔끔한 폰트 & 뱃지)
st.markdown("""
    <style>
    /* 메인 배경 및 기본 폰트 */
    .main {
        background-color: #F8FAF8;
    }
    
    /* 타이틀 텍스트 스타일 */
    .title-header {
        color: #1b4332;
        font-weight: 800;
        margin-bottom: 5px;
    }
    
    /* 카드 컨테이너 스타일 */
    .custom-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9f5ed;
        margin-bottom: 20px;
    }
    
    /* 긍정적인 감축 성공 카드 */
    .card-success {
        border-left: 6px solid #2d6a4f;
        background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
    }
    
    /* 경고/배출 증가 카드 */
    .card-warning {
        border-left: 6px solid #d62728;
        background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
    }
    
    /* 메트릭 강조 숫자 */
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1b4332;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #52b788;
        font-weight: 600;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #F0F7F2;
        border-right: 1px solid #d8ebd9;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 경로 설정 (GitHub 환경 호환)
BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "data" / "clean"

# 4. 엔진 로드
try:
    from shift_engine import ShiftEngine
except ImportError:
    import sys
    sys.path.append(str(BASE_DIR))
    from shift_engine import ShiftEngine

@st.cache_resource
def load_engine():
    return ShiftEngine(CLEAN_DIR)

try:
    E = load_engine()
except Exception as e:
    st.error(f"데이터 엔진 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# --- 사이드바: 설정 및 안내 ---
st.sidebar.markdown("### 🎛️ 시뮬레이션 조건 설정")

season = st.sidebar.selectbox("계절 선택", ["전체", "봄", "여름", "가을", "겨울"], index=1)
day_type = st.sidebar.selectbox("요일 구분", ["전체", "평일", "휴일"], index=1)
scenario = st.sidebar.selectbox(
    "배출계수 기준 (시나리오)",
    options=["mid", "min", "max", "direct"],
    format_func=lambda x: {
        "mid": "IPCC 전과정 중앙값 (기본)",
        "min": "IPCC 전과정 최소",
        "max": "IPCC 전과정 최대",
        "direct": "직접배출 (연소 직후)"
    }[x]
)

season_arg = None if season == "전체" else season
day_arg = None if day_type == "전체" else day_type

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **핵심 메시지**\n\n"
    "\"같은 전기도 언제 쓰느냐에 따라 탄소 배출이 달라집니다.\"\n\n"
    "🌱 **평균 9% 감축** (일별 3~22%)\n"
    "⚠️ 하지만 시간 이동보다 **전체 절약이 최우선**입니다!"
)

# --- 메인 타이틀 & 배너 ---
st.markdown("<h1 class='title-header'>⚡ 스마트 전력 사용 및 탄소 배출량 이동 시뮬레이터</h1>", unsafe_allow_html=True)
st.markdown(
    "전력 수요를 깨끗한 시간대로 옮겨 탄소 배출을 줄이는 **수요 이동(Load Shifting)** 효과를 "
    "실제 전력 거래 데이터와 전력원별 구성으로 정밀하게 분석합니다."
)
st.markdown("<br>", unsafe_allow_html=True)

# 요약 메트릭 계산
h_ci = E.hourly_ci(season=season_arg, day_type=day_arg, scenario=scenario)
annual_mean = h_ci.mean()
min_hour, min_val = int(h_ci.idxmin()), h_ci.min()
max_hour, max_val = int(h_ci.idxmax()), h_ci.max()

# 대시보드 상단 미감 개선 카드 3종
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
        <div class="custom-card">
            <div class="metric-label">선택 조건 평균 탄소집약도</div>
            <div class="metric-value">{annual_mean:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="custom-card" style="border-top: 4px solid #2d6a4f;">
            <div class="metric-label">☀️ 가장 깨끗한 시간 ({min_hour}시)</div>
            <div class="metric-value" style="color:#2d6a4f;">{min_val:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
            <span style="color:#2d6a4f; font-weight:bold; font-size:0.85rem;">↓ {abs(min_val - annual_mean):.1f} g 절감</span>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="custom-card" style="border-top: 4px solid #d62728;">
            <div class="metric-label">🔥 가장 배출이 많은 시간 ({max_hour}시)</div>
            <div class="metric-value" style="color:#d62728;">{max_val:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
            <span style="color:#d62728; font-weight:bold; font-size:0.85rem;">↑ {abs(max_val - annual_mean):.1f} g 과다</span>
        </div>
    """, unsafe_allow_html=True)

# --- 탭 구성 ---
tabs = st.tabs([
    "📈 탄소 곡선 & 발전원",
    "🗺️ 연중 히트맵 & 분포",
    "⚡ 스마트 시뮬레이터",
    "📊 정직한 결과 & 한계",
    "📚 데이터 & 방법론"
])

# ==========================================
# [Tab 1] 탄소 곡선 & 발전원
# ==========================================
with tabs[0]:
    st.subheader("📈 24시간 시간대별 탄소집약도 곡선")
    st.markdown("하루 중 시간에 따라 전력 시스템의 탄소집약도가 어떻게 변하는지 확인합니다. (정오 무렵 최저, 저녁 피크 시각 최고)")

    hours = list(range(24))
    ci_values = [h_ci.get(h, annual_mean) for h in hours]

    fig_curve = px.line(
        x=hours, y=ci_values,
        labels={"x": "시각 (Hour)", "y": "탄소집약도 (g/kWh)"},
        markers=True,
        title=f"[{season} / {day_type}] 시간대별 탄소집약도 추이"
    )
    fig_curve.update_traces(line_color="#2d6a4f", line_width=3, marker_size=8)
    fig_curve.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(tickmode='linear', dtick=1, gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0")
    )
    st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("---")
    st.subheader("☀️ 왜 정오가 가장 깨끗할까요? (전력원별 구성 분석)")
    st.markdown("태양광 발전 비중이 급증하는 정오(12~14시)에는 탄소 배출이 많은 LNG 및 석탄 발전 비중이 상대적으로 감소합니다.")

    mix_path = CLEAN_DIR / "fuel_hour_mix.csv"
    if mix_path.exists():
        mix_df = pd.read_csv(mix_path)
        sub_mix = mix_df[(mix_df.season == season) & (mix_df.day_type == day_type)]
        if sub_mix.empty:
            sub_mix = mix_df[(mix_df.season == "전체") & (mix_df.day_type == "전체")]

        fig_mix = px.bar(
            sub_mix, x="hour", y="mwh_mean", color="group",
            labels={"hour": "시각 (Hour)", "mwh_mean": "평균 발전량 (MW)", "group": "전력원"},
            title="시간대별 전력원별 평균 발전량 구성",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_mix.update_layout(
            barmode="stack",
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            xaxis=dict(tickmode='linear', dtick=1, gridcolor="#f0f0f0")
        )
        st.plotly_chart(fig_mix, use_container_width=True)
    else:
        st.info("전력원별 구성 데이터(fuel_hour_mix.csv)를 찾을 수 없습니다.")

# ==========================================
    # [Tab 2] 연중 히트맵 & 분포 (디자인 업그레이드된 히스토그램)
    # ==========================================
    with tabs[1]:
        st.subheader("🗺️ 월별 × 시간대 탄소집약도 히트맵")
        st.markdown("1년 365일 동안 월과 시간에 따라 탄소집약도가 어떻게 분포하는지 거시적인 패턴을 조망합니다.")

        month_hour_path = CLEAN_DIR / "ci_month_hour.csv"
        if month_hour_path.exists():
            mh_df = pd.read_csv(month_hour_path)
            mh_pivot = mh_df.pivot(index="month", columns="hour", values="ci_mid")
            fig_hm = px.imshow(
                mh_pivot,
                labels=dict(x="시각 (Hour)", y="월 (Month)", color="g/kWh"),
                x=mh_pivot.columns,
                y=mh_pivot.index,
                color_continuous_scale="Viridis",
                title="월별-시간대별 평균 탄소집약도 히트맵"
            )
            # 히트맵 배경 및 여백 정돈
            fig_hm.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_hm, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 날짜별 이동 감축률 분포 (365일)")
        st.markdown("동일한 시간 이동(예: 19시 → 12시, 2시간)을 하더라도, 날마다 전력 상황에 따라 감축 효과가 3% ~ 22%로 다르게 나타납니다.")

        dd_s = E.daily_distribution()
        median_val = dd_s.median()  # 분포의 중앙값 계산

        # 1. 히스토그램 객체 생성
        fig_hist = px.histogram(
            x=dd_s, nbins=30,
            labels={"x": "이동 감축률 (%)", "count": "일수 (Days)"},
            title="365일 일별 이동 감축률 분포 및 중앙값 분석"
        )
        
        # 2. 바(Bar) 스타일 정교화 (부드러운 투명도와 테두리선 부여)
        fig_hist.update_traces(
            marker_color="#2d6a4f", 
            marker_line_color="#1b4332", 
            marker_line_width=1.2,
            opacity=0.85
        )
        
        # 3. 핵심 포인트인 '중앙값' 수직선(Line)과 라벨 추가로 정보성 및 시각적 완성도 극대화
        fig_hist.add_vline(
            x=median_val, 
            line_dash="dash", 
            line_color="#d62728", 
            annotation_text=f"중앙값: {median_val:.1f}%", 
            annotation_position="top right",
            annotation_font=dict(size=12, color="#d62728", family="sans-serif")
        )

        # 4. 레이아웃 미감 극대화 (배경 투명화, 그리드 은은하게 처리)
        fig_hist.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="sans-serif", size=12, color="#262730"),
            xaxis=dict(
                gridcolor="#E5E7EB", 
                zeroline=False, 
                showline=True, 
                linewidth=1, 
                linecolor="#D1D5DB"
            ),
            yaxis=dict(
                gridcolor="#E5E7EB", 
                zeroline=False, 
                showline=True, 
                linewidth=1, 
                linecolor="#D1D5DB"
            ),
            margin=dict(l=40, r=40, t=60, b=40),
            title_font=dict(size=16, color="#1b4332", family="sans-serif")
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# [Tab 3] 스마트 이동 시뮬레이터 (핵심 디테일 수정 적용)
# ==========================================
with tabs[2]:
    st.subheader("⚡ 스마트 전력 이동 시뮬레이터")
    st.markdown("가전제품이나 전력 사용 활동을 저녁 피크 시간대에서 깨끗한 낮 시간대로 옮겼을 때의 감축 효과를 실시간으로 계산합니다.")

    col_in1, col_in2 = st.columns(2)

    with col_in1:
        input_mode = st.radio("전력량 입력 방식", ["가전 프리셋 선택", "직접 입력 (kWh)"])

        presets_path = CLEAN_DIR / "activity_presets.csv"
        kwh = 1.0
        preset_name = ""
        if input_mode == "가전 프리셋 선택" and presets_path.exists():
            p_df = pd.read_csv(presets_path)
            preset_choice = st.selectbox("가전제품 선택", p_df["category"].tolist())
            row_p = p_df[p_df["category"] == preset_choice].iloc[0]
            preset_name = row_p["category"]
            
            # [검증 가이드 반영] 414.9 g/kWh는 한국 전력망 평균 탄소집약도 환산 기준입니다.
            default_kwh = row_p["co2_median"] / 414.9
            kwh = st.slider("전력량 (kWh) [상대 추정]", 0.1, 10.0, float(round(default_kwh, 2)), 0.1)
            st.caption(f"📌 선택 품목: **{preset_name}** | 표준 1회 배출량 기준: {row_p['co2_median']:.1f} g (한국 전력망 평균 414.9g/kWh 기준 약 {kwh:.2f} kWh 환산)")
        else:
            kwh = st.number_input("전력량 (kWh)", min_value=0.1, max_value=100.0, value=1.5, step=0.1)

        from_time = st.slider("원래 시작 시각 (From)", 0, 23, 19)
        duration = st.slider("활동 지속 시간 (시간)", 1, 6, 2)

    with col_in2:
        to_time = st.slider("이동할 목표 시작 시각 (To)", 0, 23, 12)
        sim_season = st.selectbox("시뮬레이션 계절", ["봄", "여름", "가을", "겨울"], index=0)
        sim_day = st.selectbox("시뮬레이션 요일 구분", ["평일", "휴일"], index=0)

    if st.button("🚀 이동 효과 시뮬레이션 실행", type="primary"):
        r = E.shift(kwh=kwh, from_start=from_time, to_start=to_time, duration=duration, season=sim_season, day_type=sim_day, scenario=scenario)
        band = E.shift_band(kwh=kwh, from_start=from_time, to_start=to_time, duration=duration, season=sim_season, day_type=sim_day)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🎯 시뮬레이션 결과 리포트")

        saved_g = r.get('saved_g', r.get('saved', 0))
        saved_rate = r.get('saved_rate', r.get('rate', 0))
        
        # 💡 불확실성 분석 테이블(band)에서 현재 선택된 시나리오의 ci_from, ci_to를 가져와 배출량 계산
        try:
            matched_row = band[band['scenario'] == scenario]
            if not matched_row.empty:
                ci_from = matched_row.iloc[0]['ci_from']
                ci_to = matched_row.iloc[0]['ci_to']
            else:
                ci_from = band.iloc[0]['ci_from']
                ci_to = band.iloc[0]['ci_to']
            
            emission_before = kwh * ci_from
            emission_after = kwh * ci_to
        except:
            emission_before = 0.0
            emission_after = 0.0

        # 아예 안 쓸 때 절약량은 이동 전 배출량(전기 사용으로 인한 총 배출량)과 같습니다.
        saved_g_noreduce = emission_before

        # 탄소 감축 여부에 따른 동적 메시지 및 카드 분기
        if saved_g >= 0:
            st.markdown(f"""
                <div class="custom-card card-success">
                    <h3 style="color: #2d6a4f; margin:0;">🌱 친환경 스마트 이동 성공!</h3>
                    <p style="margin-top:8px; font-size: 1.05rem; color:#262730;">
                        <b>{from_time}시</b>에서 <b>{to_time}시</b>로 이동하여 <b>{saved_g:.1f} g</b>의 탄소 배출을 줄였습니다. 
                        (전력 탄소 집약도 <b>{saved_rate*100:.1f}% 감축</b> 효과)
                    </p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="custom-card card-warning">
                    <h3 style="color: #d62728; margin:0;">⚠️ 주의: 탄소 배출량이 오히려 증가합니다!</h3>
                    <p style="margin-top:8px; font-size: 1.05rem; color:#262730;">
                        <b>{from_time}시</b>보다 <b>{to_time}시</b>의 전력 집약도가 더 높습니다. 
                        이동 시 탄소 배출량이 <b>{abs(saved_g):.1f} g 증가 (+{abs(saved_rate)*100:.1f}%)</b>하므로 이 시간대는 피하는 것이 좋습니다.
                    </p>
                </div>
            """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "변동 탄소량", 
            f"{abs(saved_g):.1f} g", 
            delta=f"{saved_rate*100:.1f}% {'감축' if saved_g >= 0 else '증가'}", 
            delta_color="normal" if saved_g >= 0 else "inverse"
        )
        m2.metric("이동 전 배출량", f"{emission_before:.1f} g")
        m3.metric("이동 후 배출량", f"{emission_after:.1f} g")
        m4.metric("아예 안 쓸 때 (절약)", f"{saved_g_noreduce:.1f} g", help="절약(Reduction)은 언제나 이동(Shifting)보다 강력합니다.")

        if saved_g > 0:
            annual_saved_kg = (saved_g * 365) / 1000
            pine_trees = annual_saved_kg / 6.6
            car_km = annual_saved_kg / 0.192

            st.info(
                f"🌿 **일상 속 환산 효과 (매일 실천 시)**\n\n"
                f"- 연간 **{annual_saved_kg:.1f} kg**의 CO₂ 절감\n"
                f"- **소나무 약 {pine_trees:.1f}그루**가 1년 동안 흡수하는 탄소량\n"
                f"- **내연기관차 약 {car_km:.1f} km** 주행 시 발생하는 탄소 절감 효과"
            )

        st.markdown("#### 🔬 계수 세트별 비교 (불확실성 분석)")
        st.dataframe(band.round(3), use_container_width=True)

        st.markdown("#### ✨ 이 시간대에 하세요! (가장 깨끗한 시작 시각 Top 3)")
        best_df = E.best_start(duration=duration, season=sim_season, day_type=sim_day, scenario=scenario)
        st.dataframe(best_df.head(3).round(3), use_container_width=True)

# ==========================================
# [Tab 4] 정직한 결과 & 한계 (디자인 & 스토리텔링 대폭 강화)
# ==========================================
with tabs[3]:
    st.markdown("### 📊 정직한 결과: 왜 감축 효과가 작아 보일까요?")
    st.markdown(
        "탄소 배출량 감소율은 **어떤 기준(분모)을 적용하느냐**에 따라 수치가 극적으로 달라집니다. "
        "본 연구는 효과를 과장하지 않고, 3가지 기준을 투명하게 비교하여 **수요 이동(Shifting)의 냉정한 한계**를 직시합니다."
    )

    denoms = E.denominators(p=0.1, season=season_arg, day_type=day_arg)
    
    # 3가지 분모 기준을 인포그래픽 카드 형태로 시각화
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        st.markdown(f"""
            <div class="custom-card" style="border-top: 4px solid #2d6a4f; text-align: center;">
                <div style="font-size: 0.85rem; color: #52b788; font-weight: bold;">기준 ① 이동분 기준 (Moved Share)</div>
                <div style="font-size: 2rem; font-weight: 800; color: #1b4332; margin: 10px 0;">{denoms['moved_rate']*100:.1f}%</div>
                <p style="font-size: 0.85rem; color: #666; margin: 0;">실제 이동한 전력량 내에서의 상대적 감축 효과 (체감 효과)</p>
            </div>
        """, unsafe_allow_html=True)

    with col_d2:
        st.markdown(f"""
            <div class="custom-card" style="border-top: 4px solid #40916c; text-align: center;">
                <div style="font-size: 0.85rem; color: #52b788; font-weight: bold;">기준 ② 저녁 총사용량 기준</div>
                <div style="font-size: 2rem; font-weight: 800; color: #1b4332; margin: 10px 0;">{denoms['evening_rate']*100:.1f}%</div>
                <p style="font-size: 0.85rem; color: #666; margin: 0;">저녁 피크 시간 전체 사용량 대비 기여도</p>
            </div>
        """, unsafe_allow_html=True)

    with col_d3:
        st.markdown(f"""
            <div class="custom-card" style="border-top: 4px solid #d62728; text-align: center;">
                <div style="font-size: 0.85rem; color: #e56b6f; font-weight: bold;">기준 ③ 일일 총사용량 기준 (시장 전체)</div>
                <div style="font-size: 2rem; font-weight: 800; color: #d62728; margin: 10px 0;">{denoms['daily_rate_market']*100:.2f}%</div>
                <p style="font-size: 0.85rem; color: #666; margin: 0;">하루 국가 전체 총배출량 대비 실제 비율 (냉정한 현실)</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 요약 테이블 추가
    denom_df = pd.DataFrame([
        {"분모 기준": "이동분 기준 (Moved Share, p=10%)", "감소율(%)": f"{denoms['moved_rate']*100:.2f}%", "해석 및 의미": "개별 활동 관점에서는 약 9~10%의 유의미한 감축 가능"},
        {"분모 기준": "저녁 총사용량 기준 (Evening Total)", "감소율(%)": f"{denoms['evening_rate']*100:.2f}%", "해석 및 의미": "피크 타임 전체 부하 중 일부가 이동하는 효과"},
        {"분모 기준": "일일 총사용량 기준 (실제 시장)", "감소율(%)": f"{denoms['daily_rate_market']*100:.2f}%", "해석 및 의미": "거대 전력망 전체를 기준으로 할 때 개인이 미치는 물리적 영향의 한계"},
    ])
    st.dataframe(denom_df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⚠️ 본 연구가 말하는 진정한 시사점 (한계와 제언)")
    
    st.markdown("""
        <div class="custom-card" style="background-color: #f8f9fa; border-left: 5px solid #1b4332;">
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6; color: #262730;">
                <li><b>개인 행동의 한계 (효과의 미비성):</b> 전력망 전체의 거대한 규모에 비추어볼 때, 가전제품 몇 개를 시간대별로 옮기는 '수요 이동(Shifting)'만으로는 국가 단위 탄소 감축에 극적인 변화를 이끌어내기 어렵습니다. (일일 기준 약 0.3%)</li>
                <li><b>절약(Reduction)의 절대적 우위:</b> 따라서 전기를 깨끗한 시간에 쓰는 것보다, <b>전기 사용량 자체를 줄이는 '절약'이 언제나 최우선 순위</b>여야 합니다.</li>
                <li><b>그럼에도 이동(Shifting)이 필요한 이유:</b> 향후 재생에너지(태양광·풍력) 비중이 급증할 미래 전력 시장에서는 낮 시간에 발생하는 '전력 과잉 생산(출력 제어 문제)'을 흡수하기 위해 스마트 수요 이동 기술이 필수적인 제도적 장치가 됩니다.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# [Tab 5] 데이터 & 방법론
# ==========================================
with tabs[4]:
    st.subheader("📚 데이터 출처 및 방법론 요약")
    st.markdown(
        "본 프로젝트는 공공 데이터와 투명한 알고리즘을 바탕으로 구축되었습니다.\n\n"
        "1. **전력거래소 (KPX) 시간별 발전원별 전력데이터:** 2025년 기준 전국 발전원별 실시간 발전량 및 탄소배출계수\n"
        "2. **IPCC 기후변화에 관한 정부간 협의체 가이드라인:** 전과정 탄소배출계수 (최소/중앙/최대 세트)\n"
        "3. **환경부 및 한국에너지공단 표준 자료:** 가전제품 표준 전력 소비량 및 탄소 배출 통계\n"
        "4. **데이터 처리 파이프라인:** Pandas를 활용한 결측치 정제, 일자별/계절별 분류, 거래시간(1~24) 정규화\n\n"
        "💻 **GitHub 저장소:** [프로젝트 소스코드 링크 바로가기](https://github.com/)\n"
        "🤖 **AI 협업 내역:** 고성능 AI 협업을 통해 엔진 검증 및 Streamlit 대시보드를 구축하였습니다."
    )

st.markdown("---")
st.caption("© 2026 데이터분석연구회 | Smart Carbon Shifting Project — All Rights Reserved.")
