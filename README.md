# ⚡ CARBON SHIFT (전력 수요 이동 및 탄소 감축 시뮬레이터)
> **"전기는 언제 쓰느냐에 따라 탄소 배출량이 달라집니다."**  
> **TEAM WHENWHATWATT | 2026 Data Research and Analysis**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://2026dataanalysiscarbon-whenwhat2watt.streamlit.app/)

---

## 📌 1. 프로젝트 개요 (Overview)

본 프로젝트는 전력거래소(KPX)의 실시간 발전원별 전력 데이터와 IPCC(기후변화에 관한 정부간 협의체) 배출계수를 결합하여, 전력 사용 시간대를 변경했을 때 발생하는 **탄소 감축 효과(Load Shifting)**를 다각도로 분석한 데이터 연구 및 웹 시뮬레이터입니다.

국가 전력망 전체의 거시적 한계(일일 총배출량 기준 감축률 약 0.3%)와 함께, **가정·학교·교실 단위의 마이크로 스케일(Micro Scale)에서 실천할 수 있는 미시적 가치**를 정직하고 명확하게 전달하는 것을 목표로 합니다.

---

## 🏗️ 2. 시스템 아키텍처 및 파이프라인

```text
[원천 데이터 (KPX/IPCC/KEA)]
         ↓
[01_prepare_data.py] → 8,760시간 전처리 & IPCC 계수 매핑 (data/clean/)
         ↓
[02_feedback_checks.py] → 불확실성 검증 & 3가지 분모 정밀 시나리오 산출
         ↓
[shift_engine.py] → 시간 이동 계산 엔진 (Shift, Band, Distribution)
         ↓
[app.py] → Streamlit 기반 웹 대시보드 (CARBON SHIFT)
```

---

## 📂 3. 데이터 세트 상세 (`data/clean/`)

| 파일명 | 주요 내용 | 활용 파트 |
|---|---|---|
| `fuel_map.csv` | KPX 26개 연료원 ➔ IPCC 기술 세트 및 배출계수(min/mid/max/direct) 매핑 | 전력원 탄소 계산 |
| `ipcc_factors.csv` | IPCC 전과정(LCA) 및 직접 배출계수 산출 표 | 데이터 출처 대조 |
| `ci_dayhour.csv` | 2025년 8,760시간 전체 탄소집약도, 총 거래량, 태양광 비중 | 핵심 백엔드 DB |
| `ci_season_hour.csv` | 계절별 × 요일별(평일/휴일) × 24시간 평균 탄소집약도 및 분위수 | [Tab 1] 곡선 차트 |
| `ci_month_hour.csv` | 월별 × 24시간 탄소집약도 매트릭스 | [Tab 2] 연중 히트맵 |
| `fuel_hour_mix.csv` | 시간대별 전력원별(태양광, 원전, 가스, 석탄 등) 평균 발전량 구성 | [Tab 1] 발전원 분석 |
| `activity_presets.csv` | 주요 가전제품 1회/1시간 사용 시 탄소 배출량 및 kWh 환산값 | [Tab 3] 시뮬레이터 |

---

## 🧮 4. 핵심 분석 방법론 및 계산 로직

### ① 탄소집약도 (Carbon Intensity, CI) 산출
$$CI_h = \frac{\sum_{i} (MW_{h,i} \times EF_i)}{\sum_{i} MW_{h,i}} \quad (g/kWh)$$
* $MW_{h,i}$: $h$시간대의 $i$번째 발전원 거래량
* $EF_i$: $i$번째 발전원의 IPCC 탄소배출계수

### ② 정직한 결과: 감소율을 바라보는 3가지 분모 기준
1. **이동분 기준 (Moved Share, $p=10\%$):**  
   $$\text{Rate}_{\text{moved}} = \frac{CI_{\text{evening}} - CI_{\text{noon}}}{CI_{\text{evening}}}$$  
   *(해석: 이동한 개별 가전/활동 관점에서는 약 9~10%의 유의미한 감축 효과)*
2. **저녁 총사용량 기준 (Evening Total):**  
   $$\text{Rate}_{\text{evening}} = p \times \text{Rate}_{\text{moved}}$$  
   *(해석: 저녁 피크 타임 전체 부하 중 낮으로 전환된 비중)*
3. **일일 총사용량 기준 (실제 전력 시장):**  
   $$\text{Rate}_{\text{daily}} = p \times \left(\frac{\text{Evening Consumption}}{\text{Daily Total}}\right) \times \text{Rate}_{\text{moved}}$$  
   *(해석: 거대 국가 전력망 전체 관점에서는 약 0.3% 수준의 물리적 한계 직시)*

---

## 💻 5. 주요 기능 및 웹 앱 구성 (`app.py`)

- **📈 [Tab 1] 탄소 곡선 & 발전원:** 시간대별 탄소집약도 추이 및 정오 무렵 태양광 발전 급증에 따른 발전원 구성(Mix) 시각화 및 실시간 동적 인사이트 제공.
- **🗺️ [Tab 2] 연중 히트맵 & 365일 분포:** 월×시간대 히트맵 및 365일 이동 감축률 히스토그램 내 **중앙값(Median) 수직선**으로 신뢰성 보장.
- **⚡ [Tab 3] 스마트 시뮬레이터:** 가전제품 프리셋 및 전력량 선택 후 저녁 ➔ 낮 시간 이동 시 **탄소 변동량, 실시간 붉은색 경고/초록색 성과 카드, 소나무·자동차 환산 가치** 제공.
- **📊 [Tab 4] 정직한 결과 & 한계:** 3가지 분모 기준 투명 비교 및 가정·학교 마이크로 스케일 실천 가치 논의.
- **📚 [Tab 5] 데이터 & 방법론:** 출처 명시 및 파이프라인 개요.

---

## 🛠️ 6. 실행 가이드 (Quick Start)

### 환경 설정 및 패키지 설치
```bash
git clone https://github.com/your-repo/2026data_analysis_carbon.git
cd 2026data_analysis_carbon
pip install pandas openpyxl holidays streamlit plotly
```

### 전처리 및 데이터 파이프라인 실행
```bash
python scripts/01_prepare_data.py "2026_데이터분석_연구__데이터.xlsx"
python scripts/02_feedback_checks.py "2026_데이터분석_연구__데이터.xlsx"
python scripts/03_check_engine.py
```

### Streamlit 웹 앱 로컬 실행
```bash
streamlit run app.py
```

---

## 👥 7. 팀 정보 (Team Information)

* **Team Name:** WHENWHATWATT
* **Project Name:** CARBON SHIFT (2026 Data Research and Analysis)
* **Core Philosophy:** "거시적 전력망의 한계를 직시하고, 일상 속 작은 습관 변화가 만드는 위대한 친환경 가치를 증명합니다."
