"""
[1단계] 데이터 정리: 원본 4개 표 -> 분석용 CSV
실행:  python 01_prepare_data.py "2026_데이터분석_연구__데이터.xlsx"
결과:  ../data/clean/*.csv  (모두 GitHub 25MB 제한 안)

코드는 6개 구역(A~F)으로 나뉘어 있고, 위에서 아래로 한 번만 실행하면 됩니다.
  A. KPX 시간별 자료 읽기와 검사      (데이터 1)
  B. IPCC 배출계수 표 숫자로 바꾸기   (데이터 4)
  C. 연료원 대응표 만들기             (KPX 연료원 -> IPCC 기술 -> 계수)
  D. 시간별 탄소집약도 계산           (핵심 계산)
  E. EPSIS 설비용량과 비교            (데이터 2, 범위 검증)
  F. 에너지공단 제품 표 정리          (데이터 3)
"""
import sys, re
from pathlib import Path
import numpy as np
import pandas as pd
import holidays

XLSX = Path(sys.argv[1] if len(sys.argv) > 1 else "2026_데이터분석_연구__데이터.xlsx")
OUT = Path(__file__).resolve().parent.parent / "data" / "clean"
OUT.mkdir(parents=True, exist_ok=True)

# ---- 팀이 정해야 하는 값 (지금은 비워 둠) -------------------------------------
KEA_EF_G_PER_KWH = None   # 에너지공단 라벨의 CO2 환산계수(g/kWh). 확인되면 숫자로 채움
NOON_HOURS = [13, 14]     # 거래시간 13,14 = 12~14시  (거래시간 h = (h-1)시~h시)
EVE_HOURS = [20, 21]      # 거래시간 20,21 = 19~21시
# -------------------------------------------------------------------------------

sheets = pd.ExcelFile(XLSX).sheet_names
print("탭:", sheets)

# =============================== A. KPX 읽기와 검사 =============================
kpx = pd.read_excel(XLSX, sheet_name=sheets[0])
kpx.columns = ["date", "hour", "fuel", "cap_mw", "mwh"]       # 영문 열 이름으로 통일
kpx["date"] = pd.to_datetime(kpx["date"])

# 검사: 하루 24시간이 모두 있는지, (날짜,시간,연료원) 중복이 없는지, 빈 값이 없는지
assert kpx["date"].nunique() == 365, "날짜 수가 365가 아님"
assert set(kpx["hour"].unique()) == set(range(1, 25)), "거래시간이 1~24가 아님"
assert not kpx.duplicated(["date", "hour", "fuel"]).any(), "중복 행이 있음"
assert not kpx.isna().any().any(), "빈 값이 있음"
n_neg = int((kpx["mwh"] < 0).sum())
print(f"KPX 행 {len(kpx):,} | 연료원 {kpx['fuel'].nunique()}종 | 음수 {n_neg}건")
kpx["mwh"] = kpx["mwh"].clip(lower=0)                           # 음수는 0 처리(계획서 3번)

# 날짜 구분: 계절, 평일/휴일(주말+공휴일)
kr_holidays = holidays.country_holidays("KR", years=2025)       # 공식 달력과 꼭 대조할 것
m = kpx["date"].dt.month
kpx["month"] = m
kpx["season"] = np.select([m.isin([3, 4, 5]), m.isin([6, 7, 8]), m.isin([9, 10, 11])],
                          ["봄", "여름", "가을"], "겨울")
is_off = (kpx["date"].dt.dayofweek >= 5) | kpx["date"].dt.date.isin(kr_holidays.keys())
kpx["day_type"] = np.where(is_off, "휴일", "평일")

# =============================== B. IPCC 표 =====================================
ip = pd.read_excel(XLSX, sheet_name=sheets[3], header=None)
def parse_triplet(x):
    """'740/820/910' -> (740, 820, 910) / '0' -> (0,0,0) / 'n.a.' -> (nan,nan,nan)"""
    s = str(x).strip()
    try:
        if "/" in s:
            a, b, c = [float(v) for v in s.split("/")]
            return a, b, c
        v = float(s); return v, v, v
    except ValueError:                      # 'n.a.', 'Min/Median/Max' 같은 글자는 빈 값 처리
        return np.nan, np.nan, np.nan
rows = []
for _, r in ip.iterrows():
    name, direct, life = r[0], r[1], r[5]
    if pd.isna(direct) or pd.isna(life):        # 구분 제목·각주 행 건너뜀
        continue
    d, l = parse_triplet(direct), parse_triplet(life)
    if np.isnan(l[1]):                      # 전과정 값이 숫자가 아니면(머리글 행) 건너뜀
        continue
    rows.append([str(name).strip(), *d, *l])
ipcc = pd.DataFrame(rows, columns=["tech", "direct_min", "direct_med", "direct_max",
                                   "life_min", "life_med", "life_max"])
ipcc.to_csv(OUT / "ipcc_factors.csv", index=False, encoding="utf-8-sig")
print("IPCC 기술 수:", len(ipcc))
ipcc_i = ipcc.set_index("tech")

# =============================== C. 연료원 대응표 ===============================
# (KPX 연료원, IPCC 기술, EPSIS 열, 계산에 넣는가, 비고)
M = [
 ("원자력", "Nuclear", "원자력", True, ""),
 ("유연탄", "Coal—PC", "유연탄", True, ""),
 ("무연탄", "Coal—PC", "무연탄", True, "IPCC는 석탄 종류를 나누지 않음"),
 ("IGCC", "Coal—PC", "석탄가스화", True, "석탄 계수로 보수적으로 적용(설비 작음)"),
 ("LNG", "Gas—Combined Cycle", "LNG", True, ""),
 ("LPG", "Gas—Combined Cycle", "(확인필요)", True, "가스 계수 가정, 비중 작음"),
 ("연료전지", "Gas—Combined Cycle", "연료전지", True, "가스 계수 가정"),
 ("부생가스", "Gas—Combined Cycle", "기타", True, "가스 계수 가정(EPSIS 비고: 기타에 포함)"),
 ("가스압", None, "기타", True, "연소 없는 차압 발전 -> 0으로 둠"),
 ("경유", None, "유류", True, "IPCC에 없음 -> 보조 출처 값"),
 ("중유", None, "유류", True, "IPCC에 없음 -> 보조 출처 값"),
 ("태양광", "Solar PV—utility", "태양", True, ""),
 ("풍력", "Wind onshore", "풍력", True, "육상 기준"),
 ("수력", "Hydropower", "수력", True, "IPCC 최대값 2200은 저수지 메탄 사례"),
 ("소수력", "Hydropower", "수력", True, ""),
 ("해양에너지", "Ocean", "해양", True, ""),
 ("바이오매스", "Biomass—dedicated", "바이오", True, "직접배출은 생물기원이라 0으로 둠"),
 ("바이오가스", "Biomass—dedicated", "바이오", True, ""),
 ("바이오SRF", "Biomass—dedicated", "바이오", True, ""),
 ("바이오중유", "Biomass—dedicated", "바이오", True, ""),
 ("매립가스", "Biomass—dedicated", "바이오", True, ""),
 ("양수", None, "양수", False, "저장 방전분, 충전 전력이 기록되지 않아 제외"),
 ("급전가능 재생에너지", None, "(확인필요)", False, "구성 불명 -> 제외"),
 ("기타", None, "기타", False, "구성 불명 -> 제외"),
 ("폐기물", None, "폐기물", False, "IPCC에 없음 -> 제외"),
 ("전기저장장치(비중앙)", None, "(확인필요)", False, "연중 일부 기간만 있음 -> 제외"),
]
fm = pd.DataFrame(M, columns=["fuel", "ipcc_tech", "epsis_col", "include", "note"])
# 보조 값(IPCC에 없는 연료): 전과정 720 / 직접배출은 국내 문헌 값(경유 603, 중유 689)
manual = {"경유": dict(life=(720, 720, 720), direct=603),
          "중유": dict(life=(720, 720, 720), direct=689),
          "가스압": dict(life=(0, 0, 0), direct=0)}
fl = []
for _, r in fm.iterrows():
    if r.fuel in manual:
        lo, md, hi = manual[r.fuel]["life"]; dr = manual[r.fuel]["direct"]
        fl.append((lo, md, hi, dr, dr, dr))
    elif pd.notna(r.ipcc_tech):
        t = ipcc_i.loc[r.ipcc_tech]
        d = t.direct_med if not np.isnan(t.direct_med) else 0.0   # n.a.(바이오)는 0
        dmin = t.direct_min if not np.isnan(t.direct_min) else 0.0
        dmax = t.direct_max if not np.isnan(t.direct_max) else 0.0
        fl.append((t.life_min, t.life_med, t.life_max, dmin, d, dmax))
    else:
        fl.append((np.nan,) * 6)
fm[["f_min", "f_mid", "f_max", "dir_min", "f_dir", "dir_max"]] = pd.DataFrame(fl, index=fm.index)
assert set(fm.fuel) == set(kpx.fuel.unique()), "KPX 연료원과 대응표가 다름"
fm.drop(columns=["dir_min", "dir_max"]).to_csv(OUT / "fuel_map.csv", index=False, encoding="utf-8-sig")

# =============================== D. 탄소집약도 계산 =============================
inc = kpx.merge(fm[["fuel", "include", "f_min", "f_mid", "f_max", "f_dir"]], on="fuel")
tot_all = inc["mwh"].sum()
excl_share = inc.loc[~inc["include"], "mwh"].sum() / tot_all * 100
inc = inc[inc["include"]].copy()
print(f"계산 제외 연료 비중: {excl_share:.2f}%")
for col, name in [("f_min", "ci_min"), ("f_mid", "ci_mid"), ("f_max", "ci_max"), ("f_dir", "ci_direct")]:
    inc["em_" + name] = inc["mwh"] * inc[col]                      # 연료원별 배출량 = 거래량 x 계수
inc["solar_mwh"] = np.where(inc["fuel"] == "태양광", inc["mwh"], 0.0)
EM = ["em_ci_min", "em_ci_mid", "em_ci_max", "em_ci_direct"]

def intensity(g):
    """묶음 안의 (배출량 합) / (거래량 합) = 가중평균 탄소집약도"""
    s = g[EM + ["mwh", "solar_mwh"]].sum()
    out = {n: s["em_" + n] / s["mwh"] for n in ["ci_min", "ci_mid", "ci_max", "ci_direct"]}
    out.update(total_mwh=s["mwh"], solar_share=s["solar_mwh"] / s["mwh"] * 100)
    return pd.Series(out)

# D-1 날짜x시간(8,760행)
dh = (inc.groupby(["date", "hour", "month", "season", "day_type"], sort=True)
         .apply(intensity, include_groups=False).reset_index())
dh["date"] = dh["date"].dt.strftime("%Y-%m-%d")
dh.round(3).to_csv(OUT / "ci_dayhour.csv", index=False, encoding="utf-8-sig")

# D-2 계절 x 평일/휴일 x 시간 (평균 곡선 + 일별 변동 띠)
sh = (inc.groupby(["season", "day_type", "hour"]).apply(intensity, include_groups=False).reset_index())
band = (dh.groupby(["season", "day_type", "hour"])["ci_mid"]
          .agg(ci_mid_p25=lambda x: x.quantile(.25), ci_mid_p75=lambda x: x.quantile(.75),
               ci_mid_dmin="min", ci_mid_dmax="max", n_days="size").reset_index())
sh = sh.merge(band, on=["season", "day_type", "hour"]).drop(columns=["solar_share"])
sh.round(2).to_csv(OUT / "ci_season_hour.csv", index=False, encoding="utf-8-sig")

# D-3 월 x 시간 (히트맵용)
mh = inc.groupby(["month", "hour"]).apply(intensity, include_groups=False).reset_index()
mh.round(2).to_csv(OUT / "ci_month_hour.csv", index=False, encoding="utf-8-sig")

# D-4 월별 정오-저녁 격차와 정오 태양광 비중 (작은 질문 3)
def noon_eve(g):
    a = intensity(g[g["hour"].isin(NOON_HOURS)]); b = intensity(g[g["hour"].isin(EVE_HOURS)])
    return pd.Series(dict(noon_ci=a.ci_mid, eve_ci=b.ci_mid,
                          gap_pct=(b.ci_mid - a.ci_mid) / b.ci_mid * 100,
                          noon_solar_share=a.solar_share))
mg = inc.groupby("month").apply(noon_eve, include_groups=False).reset_index()
mg.round(2).to_csv(OUT / "ci_month_gap.csv", index=False, encoding="utf-8-sig")
print("월별 격차-태양광 비중 상관:", round(mg["gap_pct"].corr(mg["noon_solar_share"]), 2))

# 확인용 요약(예비 결과)
allh = inc.groupby("hour").apply(intensity, include_groups=False)
print(f"연평균 CI(중앙) {inc['em_ci_mid'].sum()/inc['mwh'].sum():.1f} | 최저 거래시간 {allh.ci_mid.idxmin()} "
      f"({allh.ci_mid.min():.1f}) | 최고 거래시간 {allh.ci_mid.idxmax()} ({allh.ci_mid.max():.1f})")
noon = allh.loc[NOON_HOURS, "ci_mid"].mean(); eve = allh.loc[EVE_HOURS, "ci_mid"].mean()
print(f"정오 {noon:.1f} vs 저녁 {eve:.1f} -> 이동분 기준 감소 {(eve-noon)/eve*100:.1f}%")

# =============================== E. EPSIS 설비용량 비교 ==========================
ep = pd.read_excel(XLSX, sheet_name=sheets[1], header=None)
cols = ["기간", "회원구분", "급전방식", "사업구분", "지역", "원자력", "유연탄", "무연탄", "유류", "LNG", "양수",
        "연료전지", "석탄가스화", "태양", "풍력", "수력", "해양", "바이오", "폐기물", "기타", "합계"]
ep = ep.iloc[2:].copy(); ep.columns = cols
ep = ep[ep["기간"].astype(str).str.startswith("2025/")].copy()
ep["month"] = ep["기간"].astype(str).str[-2:].astype(int)
for c in cols[5:]: ep[c] = pd.to_numeric(ep[c], errors="coerce")
# KPX 월말 설비용량(그 달 마지막 날 24시간 평균)을 같은 열 이름으로 묶음
epsis_col = fm.set_index("fuel")["epsis_col"].to_dict()
k = kpx.copy(); k["col"] = k["fuel"].map(epsis_col)
last = k.groupby("month")["date"].transform("max")
kl = k[k["date"] == last]
kc = kl.groupby(["month", "col", "fuel"])["cap_mw"].mean().groupby(["month", "col"]).sum().reset_index()
cmp_rows = []
for col in ["원자력", "유연탄", "무연탄", "LNG", "양수", "연료전지", "석탄가스화", "태양", "풍력", "수력", "해양", "바이오", "폐기물"]:
    for _, r in ep.iterrows():
        v = kc[(kc.month == r.month) & (kc["col"] == col)]["cap_mw"].sum()
        cmp_rows.append((r.month, col, v, r[col], v / r[col] * 100 if r[col] else np.nan))
tot_kpx = kl.groupby("month")["cap_mw"].sum() / 1  # 월말 하루의 24시간 설비합 -> 아래서 24로 나눔
tot_kpx = (kl.groupby("month")["cap_mw"].sum() / 24)
for _, r in ep.iterrows():
    cmp_rows.append((r.month, "합계", tot_kpx[r.month], r["합계"], tot_kpx[r.month] / r["합계"] * 100))
cov = pd.DataFrame(cmp_rows, columns=["month", "group", "kpx_cap_mw", "epsis_cap_mw", "kpx_share_pct"])
cov.round(1).to_csv(OUT / "capacity_coverage.csv", index=False, encoding="utf-8-sig")
s12 = cov[(cov.month == 12) & (cov.group == "태양")].iloc[0]
print(f"2025년 12월 태양광 설비: KPX {s12.kpx_cap_mw:,.0f}MW / EPSIS {s12.epsis_cap_mw:,.0f}MW = {s12.kpx_share_pct:.1f}%")

# =============================== F. 에너지공단 제품 표 ===========================
kea = pd.read_excel(XLSX, sheet_name=sheets[2], header=None)
hdr_rows = kea.index[kea[1].astype(str).eq("기자재명")].tolist() + [len(kea)]
spec = {"전기세탁기(일반)": ("1회", "연간"), "전기밥솥": ("1시간", "연간"),
        "의류건조기": ("1회", "연간"), "전기냉방기": ("1시간", "월간")}
def num(s): return pd.to_numeric(s.astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
tidy = []
for a, b in zip(hdr_rows[:-1], hdr_rows[1:]):
    blk = kea.iloc[a + 1:b].copy(); blk.columns = kea.iloc[a].tolist()
    cat = blk.iloc[0, 1]; use_unit, cost_period = spec[cat]
    t = pd.DataFrame({"category": cat, "model": blk.iloc[:, 2].astype(str).str.strip(),
                      "grade": blk.iloc[:, 3].astype(str).str.strip().replace({"최저소비효율기준미달": "기준미달"}),
                      "capacity_value": num(blk.iloc[:, 5]), "capacity_name": kea.iloc[a, 5],
                      "co2_per_use": num(blk.iloc[:, 6]), "use_unit": use_unit,
                      "cost": num(blk.iloc[:, 7]), "cost_period": cost_period})
    n_raw = len(t); t = t.drop_duplicates("model", keep="first")   # 모델명 중복 제거
    t.attrs["n_raw"] = n_raw; tidy.append(t)
kea_clean = pd.concat(tidy, ignore_index=True)
kea_clean.to_csv(OUT / "kea_models_clean.csv", index=False, encoding="utf-8-sig")
pres = []
for t in tidy:
    c = t["co2_per_use"].dropna(); cap = t["capacity_value"].dropna()
    row = dict(category=t["category"].iloc[0], use_unit=t["use_unit"].iloc[0], n_raw=t.attrs["n_raw"], n_clean=len(t),
               co2_median=c.median(), co2_p25=c.quantile(.25), co2_p75=c.quantile(.75), co2_min=c.min(), co2_max=c.max(),
               capacity_name=t["capacity_name"].iloc[0], capacity_median=cap.median())
    if KEA_EF_G_PER_KWH:   # 환산계수가 정해지면 kWh도 계산
        for k_ in ["co2_median", "co2_p25", "co2_p75"]:
            row[k_.replace("co2", "kwh")] = row[k_] / KEA_EF_G_PER_KWH
    pres.append(row)
pd.DataFrame(pres).round(2).to_csv(OUT / "activity_presets.csv", index=False, encoding="utf-8-sig")
print(pd.DataFrame(pres)[["category", "use_unit", "n_raw", "n_clean", "co2_median", "co2_p25", "co2_p75"]].to_string(index=False))
print("완료:", sorted(p.name for p in OUT.glob("*.csv")))
