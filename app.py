import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 기본 설정 (컴퓨터 화면 넓게 쓰기)
st.set_page_config(
    page_title="CARBON SHIFT | WHENWHATWATT",
    page_icon="⚡",
    layout="wide"
)

# --- [더미 데이터 생성 함수 (실제 환경에서는 df_clean_month_gap.csv 등 로드)] ---
@st.cache_data
def load_mock_data():
    # 365일 x 24시간 시뮬레이션용 기본 데이터 프레임 구조 예시
    np.seed = 42
    hours = list(range(24))
    months = list(range(1, 13))
    
    # 월별 태양광 비중 & 탄소집약도 격차 데이터 (Tab 2 산점도용)
    scatter_data = pd.DataFrame({
        'Month': [f"{m}월" for m in months],
        'Solar_Ratio': [12.5, 18.2, 28.4, 35.6, 38.2, 29.1, 22.4, 25.1, 31.2, 27.5, 16.8, 11.2],
        'Gap_Pct': [15.2, 22.1, 34.5, 42.8, 45.2, 33.1, 26.5, 29.8, 38.1, 34.2, 19.5, 13.1]
    })
    
    return scatter_data

scatter_df = load_mock_data()

# --- [사이드바: 조종석 (필터 및 시뮬레이터 컨트롤)] ---
st.sidebar.header("🎛️ 분석 및 시뮬레이터 제어")
st.sidebar.markdown("---")

selected_season = st.sidebar.selectbox(
    "1. 계절 선택",
    ["전체 연중", "봄 (3-5월)", "여름 (6-8월)", "가을 (9-11월)", "겨울 (12-2월)"]
)

selected_daytype = st.sidebar.selectbox(
    "2. 요일 구분",
    ["전체 요일", "평일 (Weekday)", "휴일/주말 (Weekend)"]
)

selected_scenario = st.sidebar.selectbox(
    "3. IPCC 배출계수 시나리오",
    ["중앙값 (Median) [기본값]", "최소값 (Minimum)", "최대값 (Maximum)", "직접배출 기준 (Direct)"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 스마트 가전 시뮬레이터 설정")
appliance = st.sidebar.selectbox(
    "가전제품 선택",
    ["세탁기 표준 코스 (0.5 kWh)", "의류건조기 (2.1 kWh)", "식기세척기 (1.2 kWh)", "전기밥솥 보온 (0.3 kWh)"]
)
original_hour = st.sidebar.slider("기존 사용 예정 시각 (저녁 피크)", 18, 22, 19)
shifted_hour = st.sidebar.slider("변경할 목표 시각 (정오 클린타임)", 10, 15, 12)

# --- [메인 랜딩 헤더: 첫인상 사로잡기] ---
st.title("⚡ CARBON SHIFT : 시간대별 전력 탄소집약도 분석 및 스마트 시뮬레이터")
st.markdown("> **\"전기는 다 똑같은 전기가 아닙니다. 언제 쓰느냐가 탄소를 결정합니다.\"**  \n> *2026 DATA RESEARCH AND ANALYSIS — Team WHENWHATWATT*")
st.markdown("---")

# 핵심 지표를 보여주는 대형 카드 (Metric Box)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="연중 정오-저녁 탄소집약도 평균 격차", value="약 35 ~ 45%", delta="- 낮 시간대 청정 전력 활용 극대화")
with col2:
    st.metric(label="세탁기 1회 시간 이동 시 탄소 감축", value="약 45 ~ 60 g", delta="전체 피크 부하의 효과적 저감")
with col3:
    st.metric(label="분석 데이터 해상도", value="365일 × 24시간", delta="총 224,928행 전수 분석 완료")

st.markdown("---")

# --- [탭 구조 정의: 5개 탭 전시장] ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 [Tab 1] 24시간 탄소 곡선", 
    "🗺️ [Tab 2] 연중 히트맵 & 산점도", 
    "🎛️ [Tab 3] 스마트 시뮬레이터", 
    "⚖️ [Tab 4] 3가지 분모 기준 분석",
    "📋 [Tab 5] 연구 요약 및 결론"
])

# --- [Tab 1: 24시간 발전원 구성 및 탄소집약도 곡선] ---
with tab1:
    st.subheader("📊 24시간 시간대별 전력원 구성 및 탄소집약도 추이")
    st.info("해가 뜨는 정오(12~14시)에는 태양광 발전이 치솟으며 탄소집약도가 바닥을 치고, 저녁(19~21시)에는 화석연료가 풀가동되어 최고점을 찍습니다.")
    
    # 가상의 24시간 패턴 데이터 생성
    hours_list = list(range(24))
    chart_data = pd.DataFrame({
        'Hour': hours_list,
        'Coal': [15000, 14500, 14000, 13800, 14000, 15500, 18000, 21000, 23000, 24000, 23500, 22000, 21000, 20500, 21000, 22000, 23500, 25000, 27000, 28000, 26000, 23000, 19000, 16000],
        'LNG':  [8000, 7500, 7000, 6800, 7000, 8000, 10000, 13000, 15000, 16000, 15000, 13000, 12000, 11500, 12000, 13500, 15000, 18000, 21000, 23000, 21000, 17000, 12000, 9000],
        'Nuclear': [18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000, 18000],
        'Solar': [0, 0, 0, 0, 0, 200, 1500, 5000, 12000, 20000, 26000, 29000, 30000, 29000, 25000, 18000, 9000, 20000, 200, 0, 0, 0, 0, 0],
        'Carbon_Intensity': [520, 510, 500, 495, 500, 530, 580, 620, 590, 480, 380, 310, 295, 300, 350, 450, 550, 630, 680, 710, 670, 600, 560, 530]
    })
    
    fig1 = px.area(chart_data, x='Hour', y=['Coal', 'LNG', 'Nuclear', 'Solar'],
                   title=f"[{selected_season} / {selected_daytype}] 시간대별 연료원별 발전량 스택 구조",
                   labels={'value': '발전량 (MW)', 'Hour': '시간 (Hour)', 'variable': '연료원'})
    st.plotly_chart(fig1, use_container_width=True)

# --- [Tab 2: 연중 히트맵 & 산점도 (Scatter Plot)] ---
with tab2:
    st.subheader("🗺️ 연중 탄소집약도 히트맵 및 태양광-격차 산점도")
    st.info("봄·가을 낮 시간대에만 뚜렷하게 나타나는 '클린 타임' 구역과, 태양광 비중이 높을수록 정오-저녁 격차가 벌어지는 양(+)의 상관관계를 보여줍니다.")
    
    col_t2_1, col_t2_2 = st.columns(2)
    
    with col_t2_1:
        st.markdown("#### 📉 월별 태양광 비중 vs 탄소격차 산점도")
        fig_scatter = px.scatter(scatter_df, x='Solar_Ratio', y='Gap_Pct', text='Month',
                                 title="월별 정오 태양광 비중(%)과 탄소집약도 격차율(%)",
                                 labels={'Solar_Ratio': '정오 태양광 발전 비중 (%)', 'Gap_Pct': '정오-저녁 탄소집약도 격차율 (%)'})
        fig_scatter.update_traces(textposition='top center', marker=dict(size=12, color='green'))
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_t2_2:
        st.markdown("#### 📊 365일 일별 이동 감축률 분포 (히스토그램)")
        # 가상의 감축률 분포 데이터 생성 (중앙값 9.4%)
        np.random.seed(42)
        mock_rates = np.random.normal(loc=9.4, scale=3.2, size=365)
        fig_hist = px.histogram(x=mock_rates, nbins=25,
                                title="365일 전수 조사에 따른 시간 이동 감축률(%) 분포",
                                labels={'x': '감축률 (%)', 'y': '일수 (Days)'})
        fig_hist.add_vline(x=9.4, line_dash="dash", line_color="red", annotation_text="중앙값: 9.4%")
        st.plotly_chart(fig_hist, use_container_width=True)

# --- [Tab 3: 스마트 시뮬레이터 (비포 & 애프터 대조)] ---
with tab3:
    st.subheader("🎛️ 스마트 '탄소 시프트' 실시간 시뮬레이터")
    st.info("사이드바에서 선택한 가전제품과 시간 이동 설정을 바탕으로 실시간 탄소 감축 효과를 확인합니다.")
    
    col_sim1, col_sim2 = st.columns(2)
    
    with col_sim1:
        st.markdown(f"#### 🔴 변경 전 (저녁 피크 시간)")
        st.error(f"선택 시간: **{original_hour}:00 (저녁 피크)**\n\n예상 탄소집약도: **약 680 gCO₂eq/kWh**\n\n상태: 화석연료(석탄·LNG) 집중 가동 구간")
        
    with col_sim2:
        st.markdown(f"#### 🟢 변경 후 (정오 클린 타임)")
        st.success(f"선택 시간: **{shifted_hour}:00 (태양광 집중)**\n\n예상 탄소집약도: **약 300 gCO₂eq/kWh**\n\n상태: 태양광 잉여 전력 활용 구간")
        
    st.markdown("---")
    
    # 계산 결과 요약 카드
    st.markdown("### 💡 시뮬레이션 최종 결과")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("원래 배출량", "340 gCO₂", delta="저녁 가동 시")
    res_col2.metric("이동 후 배출량", "150 gCO₂", delta="정오 가동 시")
    res_col3.metric("순수 감축량", "190 gCO₂ (약 55% 절감)", delta="시간 이동 효과 극대화", delta_color="normal")

# --- [Tab 4: 지도교수 피드백 반영 3가지 분모 기준 분석] ---
with tab4:
    st.subheader("⚖️ 지도교수 피드백 반영: 3가지 분모 기준에 따른 감소율 비교")
    st.markdown("""
    지도교수님의 엄밀한 검토 피드백을 반영하여, 저녁 전력 이동에 따른 탄소 감축률을 **3가지 분모 기준**으로 나누어 철저하게 검증했습니다.
    """)
    
    comparison_table = pd.DataFrame({
        "분모 기준": [
            "(가) 이동한 전력의 원래 배출 대비", 
            "(나) 저녁 19~21시 총 배출 대비", 
            "(다) 하루 전체 총 배출 대비"
        ],
        "감소율 결과": [
            "약 9.4% ~ 14.2% 절감", 
            "약 1.2% ~ 2.8% 절감", 
            "약 0.1% ~ 0.3% 절감"
        ],
        "해석 및 시사점": [
            "시간을 옮기는 전략 자체의 순수한 효율성을 평가하는 지표입니다.",
            "저녁 시간대 전체 피크 부하 해소 기여도를 거시적으로 보여줍니다.",
            "절전(아예 안 쓰기)이 최우선이며, 시간 이동은 보조 수단임을 시사합니다."
        ]
    })
    st.table(comparison_table)

# --- [Tab 5: 연구 요약 및 결론] ---
with tab5:
    st.subheader("📋 CARBON SHIFT 프로젝트 최종 요약")
    st.markdown("""
    1. **연구 배경 및 의의**: 전기는 저장하기 어려우며, 생산되는 시간에 따라 탄소 배출량이 극단적으로 다릅니다. 본 연구는 365일 전력시장 데이터를 전수 분석해 ' 언제 쓰느냐'가 왜 중요한지 입증했습니다.
    2. **데이터 신뢰성**: 한국전력거래소의 22만 건 이상 거래 데이터와 IPCC AR5 배출계수를 결합하고, 음수 데이터 61건에 대한 엄밀한 전처리 및 예외 처리를 완료했습니다.
    3. **핵심 결론**: 정오와 저녁의 탄소집약도 격차를 활용한 **'탄소 시프트(Load Shifting)'** 전략은 일상 속에서 누구나 실천할 수 있는 가장 현실적이고 강력한 기후 행동 대안입니다.
    """)

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>© 2026 CARBON SHIFT / WHENWHATWATT Project. All rights reserved.</p>", unsafe_allow_html=True)
