import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(
    page_title="스마트 전력 사용 및 탄소 배출량 이동 시뮬레이터",
    page_icon="⚡",
    layout="wide"
)

# 2. 경로 설정 (GitHub 환경에 맞춘 data/clean 폴더 경로)
BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "data" / "clean"

# 3. 엔진 임포트 및 로드
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

# --- 사이드바: 공통 필터 및 설정 ---
st.sidebar.header("🎛️ 시뮬레이션 설정")

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
    "\"같은 전기도 언제 쓰느냐에 따라 달라집니다.\"\n"
    "평균 9% 감축 (일별 3~22%), 하지만 하루 전체로는 절약이 먼저입니다!"
)

# --- 메인 타이틀 & 히어로 배너 ---
st.title("⚡ 스마트 전력 사용 및 탄소 배출량 이동 시뮬레이터")
st.markdown(
    "전력 수요를 깨끗한 시간대로 옮겨 탄소 배출을 줄이는 **수요 이동(Load Shifting)** 효과를 "
    "실제 전력 거래 데이터와 전력원별 구성으로 정밀하게 분석합니다."
)

# 요약 메트릭 계산
h_ci = E.hourly_ci(season=season_arg, day_type=day_arg, scenario=scenario)
annual_mean = h_ci.mean()
min_hour, min_val = int(h_ci.idxmin()), h_ci.min()
max_hour, max_val = int(h_ci.idxmax()), h_ci.max()

col1, col2, col3 = st.columns(3)
col1.metric("선택 조건 평균 탄소집약도", f"{annual_mean:.1f} g/kWh")
col2.metric(f"가장 깨끗한 시간 ({min_hour}시)", f"{min_val:.1f} g/kWh", delta=f"{min_val - annual_mean:.1f}", delta_color="inverse")
col3.metric(f"가장 더러운 시간 ({max_hour}시)", f"{max_val:.1f} g/kWh", delta=f"{max_val - annual_mean:.1f}")

st.markdown("---")

# --- 탭 구성 ---
tabs = st.tabs([
    "📈 탄소 곡선 & 발전원",
    "🗺️ 연중 히트맵 & 분포",
    "⚡ 스마트 시뮬레이터",
    "📊 정직한 결과 & 한계",
    "📚 데이터 & 방법론"
])

# ==========================================
# [Tab 1] 탄소 곡선 & 발전원 (왜 정오가 깨끗한가?)
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
    fig_curve.update_traces(line_color="#2ca02c", line_width=3, marker_size=8)
    fig_curve.update_layout(xaxis=dict(tickmode='linear', dtick=1))
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
        fig_mix.update_layout(barmode="stack", xaxis=dict(tickmode='linear', dtick=1))
        st.plotly_chart(fig_mix, use_container_width=True)
    else:
        st.info("전력원별 구성 데이터(fuel_hour_mix.csv)를 찾을 수 없습니다.")

# ==========================================
# [Tab 2] 연중 히트맵 & 분포
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
        st.plotly_chart(fig_hm, use_container_width=True)

    st.markdown("---")
    st.subheader("📊 날짜별 이동 감축률 분포 (365일)")
    st.markdown("동일한 시간 이동(예: 19시 → 12시, 2시간)을 하더라도, 날마다 전력 상황에 따라 감축 효과가 3% ~ 22%로 다르게 나타납니다.")

    dd_s = E.daily_distribution()
    fig_hist = px.histogram(
        x=dd_s, nbins=30,
        labels={"x": "이동 감축률 (%)", "count": "일수 (Days)"},
        title="365일 일별 이동 감축률 분포 (중앙값 약 9.5%)"
    )
    fig_hist.update_traces(marker_color="#1f77b4")
    st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# [Tab 3] 스마트 이동 시뮬레이터 (핵심 인터랙티브)
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
            default_kwh = row_p["co2_median"] / 414.9
            kwh = st.slider("전력량 (kWh) [상대 추정]", 0.1, 10.0, float(round(default_kwh, 2)), 0.1)
            st.caption(f"📌 선택한 품목 '{preset_name}' 표준 배출량 중앙값: {row_p['co2_median']:.1f} g (환산 전력량: {kwh:.2f} kWh)")
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

        st.markdown("---")
        st.markdown("### 🎯 시뮬레이션 결과 리포트")

        # KeyError 방지를 위해 .get()을 사용하여 안전하게 값을 가져옵니다.
        saved_g = r.get('saved_g', r.get('saved', 0))
        saved_rate = r.get('saved_rate', r.get('rate', 0))
        emission_before = r.get('emission_before', r.get('before', r.get('original_emission', 0)))
        emission_after = r.get('emission_after', r.get('after', r.get('shifted_emission', 0)))
        saved_g_noreduce = r.get('saved_g_noreduce', r.get('noreduce', 0))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("감축된 탄소량", f"{saved_g:.1f} g", delta=f"{saved_rate*100:.1f}% 감축", delta_color="normal")
        m2.metric("이동 전 배출량", f"{emission_before:.1f} g")
        m3.metric("이동 후 배출량", f"{emission_after:.1f} g")
        m4.metric("아예 안 쓸 때 감축량 (절약)", f"{saved_g_noreduce:.1f} g", help="절약은 이동 효과보다 큽니다!")

        annual_saved_kg = (saved_g * 365) / 1000
        pine_trees = annual_saved_kg / 6.6
        car_km = annual_saved_kg / 0.192

        st.info(
            f"🌿 **일상 속 환산 효과**\n"
            f"- 만약 이 행동을 **매일** 실천한다면 연간 **{annual_saved_kg:.1f} kg**의 CO₂를 줄일 수 있습니다.\n"
            f"- 이는 **소나무 약 {pine_trees:.1f}그루**가 1년 동안 흡수하는 양이거나, **내연기관차 약 {car_km:.1f} km** 주행을 줄인 효과와 같습니다."
        )

        st.markdown("#### 🔬 계수 세트별 비교 (불확실성 분석)")
        st.dataframe(band.round(3), use_container_width=True)

        st.markdown("#### ✨ 이 시간대에 하세요! (가장 깨끗한 시작 시각 Top 3)")
        best_df = E.best_start(duration=duration, season=sim_season, day_type=sim_day, scenario=scenario)
        st.dataframe(best_df.head(3).round(3), use_container_width=True)
# ==========================================
# [Tab 4] 정직한 결과 & 한계
# ==========================================
with tabs[3]:
    st.subheader("📊 정직한 결과: 분모 3가지 비교 & 한계")
    st.markdown(
        "탄소 배출량 감소율을 계산할 때 어떤 분모(기준)를 쓰느냐에 따라 수치가 달라집니다. "
        "우리 연구는 3가지 분모를 모두 투명하게 공개하여 과장 없는 정직한 결과를 도출합니다."
    )

    denoms = E.denominators(p=0.1, season=season_arg, day_type=day_arg)
    denom_df = pd.DataFrame([
        {"분모 기준": "이동분 기준 (Moved Share, p=10%)", "감소율": f"{denoms['moved_rate']*100:.2f}%", "설명": "실제 이동한 전력량 기준 감축 비율"},
        {"분모 기준": "저녁 총사용량 기준 (Evening Total)", "감소율": f"{denoms['evening_rate']*100:.2f}%", "설명": "저녁 피크 전체 사용량 대비 비율"},
        {"분모 기준": "일일 총사용량 기준 (실제 마켓)", "감소율": f"{denoms['daily_rate_market']*100:.2f}%", "설명": "하루 총배출량 대비 실제 비율 (약 0.3%)"},
    ])
    st.dataframe(denom_df, use_container_width=True)

    st.markdown("---")
    st.markdown("### ⚠️ 연구의 한계 및 시사점")
    st.markdown(
        "- **상관관계와 인과관계:** 전력 거래 데이터 분석은 통계적 상관관계를 보여주며, 특정 시간대 이동이 즉각적인 발전소 가동 중단으로 이어지는 것은 아닙니다.\n"
        "- **절약의 우선순위:** 시간 이동 효과(약 9~14%)는 유의미하지만, 전력 사용량 자체를 줄이는 **'절약(Reduction)'**이 언제나 최우선 과제입니다.\n"
        "- **실시간 변동성:** 본 연구는 과거 연평균 및 계절별 패턴을 기반으로 하므로, 실시간 재생에너지 변동성이나 기상 이변을 완벽히 반영하기에는 한계가 있습니다."
    )

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
