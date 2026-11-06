import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# 1. 페이지 설정 및 기본 레이아웃 지정
st.set_page_config(
    page_title="CARBON SHIFT | WHENWHATWATT",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 커스텀 CSS (구문 오류 정돈)
st.markdown("""
    <style>
    .main { 
        background-color: #F8FAF8; 
    }
    .title-header { 
        color: #1b4332; 
        font-weight: 800; 
        margin-bottom: 5px; 
    }
    .custom-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9f5ed;
        margin-bottom: 20px;
    }
    .card-warning {
        border-left: 6px solid #d62728;
        background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
    }
    .insight-box {
        background-color: #f0f7f2;
        border-left: 4px solid #52b788;
        padding: 16px;
        border-radius: 0 12px 12px 0;
        margin: 15px 0;
        font-size: 0.95rem;
        color: #1b4332;
        line-height: 1.6;
    }
    .badge-container { 
        display: flex; 
        gap: 10px; 
        margin-bottom: 15px; 
        flex-wrap: wrap; 
    }
    .badge-item {
        background-color: #e9f5ed; 
        color: #2d6a4f; 
        padding: 4px 12px;
        border-radius: 20px; 
        font-size: 0.85rem; 
        font-weight: 600; 
        border: 1px solid #d8ebd9;
    }
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
    [data-testid="stSidebar"] { 
        background-color: #F0F7F2; 
        border-right: 1px solid #d8ebd9; 
    }
    </style>
""", unsafe_allow_html=True)

# 3. 경로 설정
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

# --- 세션 스테이트 초기화 (다이어리 영구 저장소) ---
if "carbon_diary" not in st.session_state:
    st.session_state.carbon_diary = []

# --- 사이드바: 로고 및 설정 ---
logo_path = BASE_DIR / "logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown("---")

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
st.sidebar.markdown(
    "💡 **WHENWHATWATT 브리핑**\n\n"
    "\"전기는 언제 쓰느냐에 따라 탄소 배출량이 달라집니다.\"\n\n"
    "🌱 **현재 적용 필터**\n"
    f"- 계절: **{season}** | 요일: **{day_type}**\n"
    f"- 시나리오: **{scenario.upper()}**"
)

# --- 메인 타이틀 & 뱃지 ---
st.markdown("<h1 class='title-header'>⚡ CARBON SHIFT</h1>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="badge-container">
        <span class="badge-item">🏷️ 전력 수요 이동 (Load Shifting)</span>
        <span class="badge-item">📊 365일 × 24시간 전수 분석</span>
        <span class="badge-item">🌱 일상 속 스마트 탄소 감축</span>
    </div>
    """, 
    unsafe_allow_html=True
)
st.markdown("<p style='font-size: 1.1rem; color: #52b788; font-weight: 600;'>WHENWHATWATT | 2026 Data Research and Analysis</p>", unsafe_allow_html=True)
st.markdown(
    "전력 수요를 깨끗한 시간대로 옮겨 탄소 배출을 줄이는 **수요 이동(Load Shifting)** 효과를 "
    "실제 전력 거래 데이터와 발전원별 구성으로 정밀하게 분석하는 인터랙티브 대시보드입니다."
)
st.markdown("<br>", unsafe_allow_html=True)

# 요약 메트릭 계산
h_ci = E.hourly_ci(season=season_arg, day_type=day_arg, scenario=scenario)
annual_mean = h_ci.mean()
min_hour, min_val = int(h_ci.idxmin()), h_ci.min()
max_hour, max_val = int(h_ci.idxmax()), h_ci.max()

# 대시보드 상단 카드 3종
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
        <div class="custom-card">
            <div class="metric-label">현재 조건 평균 탄소집약도</div>
            <div class="metric-value">{annual_mean:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="custom-card" style="border-top: 4px solid #2d6a4f;">
            <div class="metric-label">☀️ 가장 깨끗한 시간 ({min_hour}시)</div>
            <div class="metric-value" style="color:#2d6a4f;">{min_val:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
            <span style="color:#2d6a4f; font-weight:bold; font-size:0.85rem;">↓ 평균 대비 {abs(min_val - annual_mean):.1f} g 절감</span>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="custom-card" style="border-top: 4px solid #d62728;">
            <div class="metric-label">🔥 가장 배출이 많은 시간 ({max_hour}시)</div>
            <div class="metric-value" style="color:#d62728;">{max_val:.1f} <span style="font-size:1.1rem; font-weight:normal;">g/kWh</span></div>
            <span style="color:#d62728; font-weight:bold; font-size:0.85rem;">↑ 평균 대비 {abs(max_val - annual_mean):.1f} g 과다</span>
        </div>
    """, unsafe_allow_html=True)

# --- 용어 정리 접이식 박스 ---
with st.expander("📖 [클릭] 연구 핵심 용어 및 배출계수 완벽 정리"):
    st.markdown("""
    ### 1. 배출계수 (Emission Factor)
    * **정의**: 특정 활동이나 연료 사용 1단위당 발생하는 온실가스(CO₂eq)의 양을 나타내는 표준 환산 계수입니다.
    ### 2. IPCC 전과정 평가 (LCA) 기준 *(기본값)*
    * **정의**: 연료의 연소 시 직접 배출뿐만 아니라 채굴, 운송, 발전소 건설까지 전 생애주기의 간접 배출을 모두 합산한 기준입니다.
    ### 3. 탄소집약도 (Carbon Intensity, gCO₂eq/kWh)
    * **정의**: 전력 1kWh를 생산할 때 공기 중에 배출되는 온실가스의 총량입니다.
    ### 4. 타임 시프팅 (Time Shifting)
    * **정의**: 전력 사용량 자체를 줄이는 '절전'과 달리 쓰는 **시간대**를 탄소 배출이 적은 시간으로 옮기는 행위입니다.
    """)
    
# --- 탭 구성 ---
tabs = st.tabs([
    "📈 탄소 곡선 & 발전원",
    "🗺️ 연중 히트맵 & 분포",
    "⚡ 스마트 시뮬레이터 & 다이어리",
    "📊 정직한 결과 & 한계",
    "📚 데이터, 전처리 & 방법론"
])

# [Tab 1] 탄소 곡선 & 발전원
with tabs[0]:
    st.subheader("📈 24시간 시간대별 탄소집약도 곡선")
    hours = list(range(24))
    ci_values = [h_ci.get(h, annual_mean) for h in hours]
    fig_curve = px.line(x=hours, y=ci_values, markers=True, title=f"[{season} / {day_type}] 시간대별 탄소집약도 추이")
    fig_curve.update_traces(line_color="#2d6a4f", line_width=3, marker_size=8)
    fig_curve.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#ffffff")
    st.plotly_chart(fig_curve, use_container_width=True)

    mix_path = CLEAN_DIR / "fuel_hour_mix.csv"
    if mix_path.exists():
        mix_df = pd.read_csv(mix_path)
        sub_mix = mix_df[(mix_df.season == season) & (mix_df.day_type == day_type)]
        if sub_mix.empty:
            sub_mix = mix_df[(mix_df.season == "전체") & (mix_df.day_type == "전체")]
        fig_mix = px.bar(sub_mix, x="hour", y="mwh_mean", color="group", title="시간대별 전력원별 평균 발전량 구성")
        st.plotly_chart(fig_mix, use_container_width=True)

# [Tab 2] 히트맵 & 분포
with tabs[1]:
    st.subheader("🗺️ 월별 × 시간대 탄소집약도 히트맵")
    month_hour_path = CLEAN_DIR / "ci_month_hour.csv"
    if month_hour_path.exists():
        mh_df = pd.read_csv(month_hour_path)
        mh_pivot = mh_df.pivot(index="month", columns="hour", values="ci_mid")
        fig_hm = px.imshow(mh_pivot, color_continuous_scale="Viridis", title="월별-시간대별 평균 탄소집약도 히트맵")
        st.plotly_chart(fig_hm, use_container_width=True)

    dd_s = E.daily_distribution()
    median_val = dd_s.median()
    fig_hist = px.histogram(x=dd_s, nbins=30, title="365일 일별 이동 감축률 분포 및 중앙값 분석")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# [Tab 3] 스마트 이동 시뮬레이터 & 다이어리 (수집 데이터 환산 전력량 기준 연동)
# ==========================================
with tabs[2]:
    st.subheader("⚡ 스마트 전력 이동 시뮬레이터 & 나의 친환경 다이어리")
    st.markdown("수집된 데이터(활동 프리셋)의 CO₂ 중앙값을 바탕으로 환산된 **기준 전력량(kWh)**을 기본값으로 로드하며, 슬라이더로 자유롭게 조정할 수 있습니다.")

    st.markdown("### 📖 나의 친환경 실천 다이어리 (Participation Log)")
    if len(st.session_state.carbon_diary) > 0:
        total_diary_saved = sum([item["절감량(g)"] for item in st.session_state.carbon_diary])
        total_pine = (total_diary_saved * 365) / 1000 / 6.6

        col_d_sum1, col_d_sum2 = st.columns(2)
        col_d_sum1.metric("누적 탄소 감축량 (실천 총합)", f"{total_diary_saved:.1f} gCO₂")
        col_d_sum2.metric("매일 실천 시 연간 소나무 환산", f"약 {total_pine:.2f} 그루 생태 기여")
        
        st.dataframe(pd.DataFrame(st.session_state.carbon_diary), use_container_width=True, hide_index=True)

        if st.button("🗑️ 다이어리 전체 초기화하기", key="clear_diary_btn"):
            st.session_state.carbon_diary = []
            st.rerun()
    else:
        st.info("💡 아래 시뮬레이터에서 이동 효과를 실행한 뒤 다이어리 기록이 자동으로 누적됩니다.")

    st.markdown("---")
    st.markdown("### 🎛️ 시뮬레이터 설정 및 실행")

    col_in1, col_in2 = st.columns(2)

    with col_in1:
        input_mode = st.radio("전력량 입력 방식", ["수집 데이터(프리셋) 기준 선택", "직접 입력 (kWh)"], key="sim_input_mode")

        presets_path = CLEAN_DIR / "activity_presets.csv"
        kwh = 1.0
        preset_name = "전기세탁기(일반)"

        if input_mode == "수집 데이터(프리셋) 기준 선택" and presets_path.exists():
            p_df = pd.read_csv(presets_path)
            preset_options = p_df["category"].tolist() if "category" in p_df.columns else p_df.iloc[:, 0].tolist()
            preset_choice = st.selectbox("수집된 가전제품/활동 선택", options=preset_options, key="sim_preset_choice")
            
            row_p = p_df[p_df["category"] == preset_choice].iloc[0] if "category" in p_df.columns else p_df.iloc[0]
            preset_name = str(row_p.get("category", "세탁기"))
            
            # 수집 데이터의 co2_median 값을 연간 평균 탄소집약도(약 414.9 g/kWh)로 나누어 실제 환산 전력량 도출
            raw_co2 = float(row_p.get("co2_median", 40.0))
            default_kwh = round(raw_co2 / 414.9, 2)
            if default_kwh < 0.1: 
                default_kwh = 0.1

            # 슬라이더를 통해 사용자가 환산 기준 전력량을 자유롭게 조절 가능
            kwh = st.slider("전력량 (kWh) [기준 값 기반 조정]", 0.1, 10.0, float(default_kwh), 0.1, key="sim_kwh_slider")
            st.caption(f"📌 수집 기준 품목: **{preset_name}** (데이터 환산 기본값: **{default_kwh} kWh**, CO₂ 중앙값: {raw_co2}g)")
        else:
            kwh = st.number_input("전력량 (kWh)", min_value=0.1, max_value=100.0, value=1.0, step=0.1, key="sim_kwh_num")

        from_time = st.slider("원래 시작 시각 (From)", 0, 23, 19, key="sim_from_slider")
        duration = st.slider("활동 지속 시간 (시간)", 1, 6, 2, key="sim_duration_slider")

    with col_in2:
        to_time = st.slider("이동할 목표 시작 시각 (To)", 0, 23, 12, key="sim_to_slider")
        sim_season = st.selectbox("시뮬레이션 계절", ["봄", "여름", "가을", "겨울"], index=0, key="sim_season_sel")
        sim_day = st.selectbox("시뮬레이션 요일 구분", ["평일", "휴일"], index=0, key="sim_day_sel")

    with st.form("simulation_form"):
        submitted = st.form_submit_button("🚀 이동 효과 시뮬레이션 실행 및 다이어리 기록", type="primary")

        if submitted:
            r = E.shift(kwh=kwh, from_start=from_time, to_start=to_time, duration=duration, season=sim_season, day_type=sim_day, scenario=scenario)
            band = E.shift_band(kwh=kwh, from_start=from_time, to_start=to_time, duration=duration, season=sim_season, day_type=sim_day)

            saved_g = r.get('saved_g', 0)
            saved_rate = r.get('saved_rate', 0)

            if saved_g >= 0:
                entry = {
                    "품목/활동": preset_name,
                    "시간 이동": f"{from_time}시 ➔ {to_time}시",
                    "계절": sim_season,
                    "절감량(g)": round(saved_g, 1)
                }
                st.session_state.carbon_diary.append(entry)
                st.success(f"🌱 [시뮬레이션 성공] {saved_g:.1f} g 감축 효과가 입증되어 **다이어리에 자동으로 기록**되었습니다!")
            else:
                st.error(f"⚠️ [경고] 해당 시간 이동은 오히려 탄소 배출량이 증가({abs(saved_g):.1f} g)하므로 다이어리에 기록되지 않습니다.")

            st.markdown("---")
            st.markdown("### 🎯 이번 실행 결과 리포트")
            
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

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("변동 탄소량", f"{abs(saved_g):.1f} g", delta=f"{saved_rate*100:.1f}% {'감축' if saved_g >= 0 else '증가'}")
            m2.metric("이동 전 배출량", f"{emission_before:.1f} g")
            m3.metric("이동 후 배출량", f"{emission_after:.1f} g")
            m4.metric("절약 효과 참고", f"{kwh * ci_from:.1f} g")

            if saved_g > 0:
                annual_saved_kg = (saved_g * 365) / 1000
                pine_trees = annual_saved_kg / 6.6
                st.info(f"🏫 연간 환산 시: **{annual_saved_kg:.1f} kg** 절감 (소나무 약 **{pine_trees:.1f}그루** 흡수량)")

            st.markdown("#### 🔬 계수 세트별 비교 (불확실성 분석)")
            st.dataframe(band.round(3), use_container_width=True)

# [Tab 4] 정직한 결과 & 한계
with tabs[3]:
    st.markdown("### 📊 정직한 결과: 왜 국가 단위 감축률은 작아 보일까요?")
    denoms = E.denominators(p=0.1, season=season_arg, day_type=day_arg)
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric("기준 ① 이동분 기준", f"{denoms['moved_rate']*100:.1f}%")
    col_d2.metric("기준 ② 저녁 총사용량", f"{denoms['evening_rate']*100:.1f}%")
    col_d3.metric("기준 ③ 시장 전체 일일", f"{denoms['daily_rate_market']*100:.2f}%")

# [Tab 5] 데이터, 전처리 & 방법론
with tabs[4]:
    st.subheader("📚 데이터 출처 및 방법론")
    st.markdown("KPX 전수 데이터 및 음수 데이터 정제(Clamping) 완료.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #666; font-size: 0.85rem;'>© 2026 WHENWHATWATT. All Rights Reserved.</p>", unsafe_allow_html=True)
