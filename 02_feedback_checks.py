"""
[피드백 반영] 지도교수 피드백 2가지를 데이터로 확인
 (1) 음수 61건: 어떤 값인지, 0 처리 전후로 결과가 달라지는지
 (2) 감소율의 분모: 이동분 / 저녁 19~21시 / 하루 전체 3가지로 나눠 계산
실행: python 02_feedback_checks.py "2026_데이터분석_연구__데이터.xlsx"   (01번 스크립트를 먼저 실행해 fuel_map.csv가 있어야 함)
결과: ../data/clean/negative_check.csv, shift_denominators.csv
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, holidays

XLSX = Path(sys.argv[1] if len(sys.argv) > 1 else "2026_데이터분석_연구__데이터.xlsx")
OUT = Path(__file__).resolve().parent.parent / "data" / "clean"
NOON, EVE = [13, 14], [20, 21]

kpx = pd.read_excel(XLSX, sheet_name=0); kpx.columns = ["date", "hour", "fuel", "cap", "mwh"]
kpx["date"] = pd.to_datetime(kpx["date"])
fm = pd.read_csv(OUT / "fuel_map.csv")
F_MID = fm.set_index("fuel")["f_mid"].to_dict()
INCL = fm.set_index("fuel")["include"].to_dict()

# ---------------------------------------------------------------- (1) 음수 확인
neg = kpx[kpx.mwh < 0]
a = kpx[kpx.fuel == "급전가능 재생에너지"]
print("음수 행", len(neg), "| 연료원:", neg.fuel.unique().tolist())
print(f"그 연료의 전체 {len(a):,}행 중 음수 {len(neg)}행 | 음수 합 {neg.mwh.sum():.1f} MWh | 같은 연료 양수 합 {a[a.mwh>0].mwh.sum():,.0f} MWh")
print("음수 값 평균 %.2f, 최소 %.2f MWh | 거래시간 1~7시 구간 %d건 / 61건" % (neg.mwh.mean(), neg.mwh.min(), neg.hour.between(1, 7).sum()))

def run(include_adjustable, clip, f_adj=48.0):
    d = kpx.copy()
    d["f"] = d.fuel.map(F_MID)
    d["inc"] = d.fuel.map(INCL)
    if include_adjustable:
        d.loc[d.fuel == "급전가능 재생에너지", ["f", "inc"]] = [f_adj, True]
    if clip: d["mwh"] = d.mwh.clip(lower=0)
    d = d[d.inc.astype(bool)].copy()
    d["em"] = d.mwh * d.f
    g = d.groupby(["date", "hour"])[["em", "mwh"]].sum()
    g["ci"] = g.em / g.mwh
    h = d.groupby("hour")[["em", "mwh"]].sum(); hci = h.em / h.mwh
    noon = h.loc[NOON, "em"].sum() / h.loc[NOON, "mwh"].sum(); eve = h.loc[EVE, "em"].sum() / h.loc[EVE, "mwh"].sum()
    return dict(annual_ci=d.em.sum() / d.mwh.sum(), min_hour=int(hci.idxmin()), min_ci=hci.min(), max_hour=int(hci.idxmax()),
                max_ci=hci.max(), noon_ci=noon, eve_ci=eve, moved_reduction_pct=(eve - noon) / eve * 100), g["ci"]

S = [("S0 기본: 급전가능 제외 + 음수 0 처리", False, True, 48), ("S1 급전가능 제외 + 음수 그대로", False, False, 48),
     ("S2 급전가능 포함(계수 48) + 음수 0 처리", True, True, 48), ("S3 급전가능 포함(계수 48) + 음수 그대로", True, False, 48),
     ("S4 급전가능 포함(계수 230) + 음수 0 처리", True, True, 230), ("S5 급전가능 포함(계수 490) + 음수 0 처리", True, True, 490)]
rows, cis = [], {}
for name, inc, clip, fadj in S:
    r, ci = run(inc, clip, fadj); r["scenario"] = name; rows.append(r); cis[name] = ci
res = pd.DataFrame(rows)[["scenario", "annual_ci", "min_hour", "min_ci", "max_hour", "max_ci", "noon_ci", "eve_ci", "moved_reduction_pct"]]
d01 = (cis[S[0][0]] - cis[S[1][0]]).abs().max(); d23 = (cis[S[2][0]] - cis[S[3][0]]).abs().max()
res["max_abs_diff_vs_pair(gCO2/kWh)"] = [0.0, d01, 0.0, d23, np.nan, np.nan]
res.round(4).to_csv(OUT / "negative_check.csv", index=False, encoding="utf-8-sig")
print(res.round(3).to_string(index=False))
print(f"\n0 처리 전후 (날짜x시간) 탄소집약도 최대 차이: 제외 시 {d01:.6f}, 포함 시 {d23:.6f} g/kWh")

# ---------------------------------------------------------------- (2) 분모 3가지
d = kpx.copy(); d["mwh"] = d.mwh.clip(lower=0); d["f"] = d.fuel.map(F_MID); d["inc"] = d.fuel.map(INCL)
d = d[d.inc.astype(bool)].copy(); d["em"] = d.mwh * d.f
kr = holidays.country_holidays("KR", years=2025)
off = (d.date.dt.dayofweek >= 5) | d.date.dt.date.isin(kr.keys())
m = d.date.dt.month
d["season"] = np.select([m.isin([3, 4, 5]), m.isin([6, 7, 8]), m.isin([9, 10, 11])], ["봄", "여름", "가을"], "겨울")
d["day_type"] = np.where(off, "휴일", "평일")

def scope_table(name, sub):
    h = sub.groupby("hour")[["em", "mwh"]].sum()
    ci_h = h.em / h.mwh
    E = h.mwh / h.mwh.sum()                                  # 시간별 사용 비중(시장 거래량 모양을 사용 패턴 대용으로 사용)
    noon = h.loc[NOON, "em"].sum() / h.loc[NOON, "mwh"].sum(); eve = h.loc[EVE, "em"].sum() / h.loc[EVE, "mwh"].sum()
    gap = eve - noon
    out = []
    for p in (0.10, 0.20, 0.30):
        moved = gap / eve                                        # (1) 이동한 전력의 원래 배출 기준(p와 무관)
        evening = p * gap / eve                                  # (2) 저녁 19~21시 총 배출 기준
        share_eve = E.loc[EVE].sum()
        daily_actual = p * share_eve * gap / (E * ci_h).sum()    # (3) 하루 전체, 시장 거래량 모양 패턴
        daily_uniform = p * (len(EVE) / 24) * gap / ci_h.mean()  # (3') 하루 전체, 24시간 고르게 사용
        out.append(dict(scope=name, p_pct=int(p * 100), noon_ci=noon, eve_ci=eve, moved_pct=moved * 100, evening_pct=evening * 100,
                        daily_actual_pct=daily_actual * 100, daily_uniform_pct=daily_uniform * 100, evening_share_of_day_pct=share_eve * 100))
    return out
tab = scope_table("연간", d)
for s in ["봄", "여름", "가을", "겨울"]:
    tab += scope_table(f"{s} 평일", d[(d.season == s) & (d.day_type == "평일")])
den = pd.DataFrame(tab)
den.round(3).to_csv(OUT / "shift_denominators.csv", index=False, encoding="utf-8-sig")
print("\n[감소율 분모 3가지 - 연간]"); print(den[den.scope == "연간"].round(3).to_string(index=False))
print("\n[봄 평일, 30% 이동]"); print(den[(den.scope == "봄 평일") & (den.p_pct == 30)].round(3).to_string(index=False))

# ---------------------------------------------------------------- (3) 효과의 크기를 현실적으로 보기
print("\n================ (3) 효과 크기 =================")
h_all = d.groupby("hour")[["em", "mwh"]].sum()
noon_all = h_all.loc[NOON, "em"].sum() / h_all.loc[NOON, "mwh"].sum()
eve_all = h_all.loc[EVE, "em"].sum() / h_all.loc[EVE, "mwh"].sum()
gap = eve_all - noon_all                                                 # g/kWh = kg/MWh
print(f"1kWh를 저녁->정오로 옮기면 약 {gap:.1f} g CO2eq 감소 (연간 평균) | 같은 1kWh를 아예 안 쓰면 약 {eve_all:.0f} g 감소")
print(f"=> 옮기기의 효과는 줄이기의 약 {gap/eve_all*100:.1f}%")
E_eve_mwh = d[d.hour.isin(EVE)].mwh.sum()
tot_em = d.em.sum()
for p in (0.1, 0.3):
    saved_t = p * E_eve_mwh * gap / 1000
    print(f"전국(시장 거래 기준) 저녁 19~21시 전력의 {int(p*100)}%를 옮기면 연 약 {saved_t:,.0f} tCO2eq, 시장 거래 전체 배출의 {saved_t*1000/tot_em*100:.3f}%")
spring_wd = d[(d.season == "봄") & (d.day_type == "평일")]; sh_ = spring_wd.groupby("hour")[["em", "mwh"]].sum()
print("봄 평일: 1kWh당 %.1f g" % (sh_.loc[EVE, "em"].sum()/sh_.loc[EVE, "mwh"].sum() - sh_.loc[NOON, "em"].sum()/sh_.loc[NOON, "mwh"].sum()))

# 날짜별 변동: 그날 저녁 대비, 07~22시(거래시간 8~22) 중 가장 깨끗한 시간으로 옮기면
g = d.groupby(["date", "hour", "season", "day_type"])[["em", "mwh"]].sum().reset_index(); g["ci"] = g.em / g.mwh
rows = []
for dt, x in g.groupby("date"):
    ev = x[x.hour.isin(EVE)]; eve_ci = ev.em.sum() / ev.mwh.sum()
    nn = x[x.hour.isin(NOON)]; noon_ci = nn.em.sum() / nn.mwh.sum()
    w = x[x.hour.between(8, 22)]; b = w.loc[w.ci.idxmin()]
    rows.append(dict(date=dt.strftime("%Y-%m-%d"), season=x.season.iloc[0], day_type=x.day_type.iloc[0], eve_ci=eve_ci, noon_ci=noon_ci,
                     best_hour=int(b.hour), best_ci=b.ci, red_to_noon_pct=(eve_ci-noon_ci)/eve_ci*100, red_to_best_pct=(eve_ci-b.ci)/eve_ci*100))
dp = pd.DataFrame(rows); dp.round(3).to_csv(OUT / "daily_potential.csv", index=False, encoding="utf-8-sig")
q = dp[["red_to_noon_pct", "red_to_best_pct"]].quantile([.1, .5, .9]).round(1); q.index = ["하위10%", "중앙값", "상위10%"]
print("\n[날짜별 이동분 감소율: 저녁 -> 정오 / 저녁 -> 07~22시 중 가장 깨끗한 시간]"); print(q.to_string())
print("정오로 옮겨도 오히려 더 더러운 날(감소율<0):", int((dp.red_to_noon_pct < 0).sum()), "일 /", len(dp))
print("\n[계절 x 평일/휴일 중앙값(저녁->정오 %)]"); print(dp.groupby(["season", "day_type"]).red_to_noon_pct.median().round(1).unstack().to_string())
print("\n[상위 5일]"); print(dp.sort_values("red_to_noon_pct", ascending=False).head(5)[["date", "season", "day_type", "eve_ci", "noon_ci", "red_to_noon_pct"]].round(1).to_string(index=False))
