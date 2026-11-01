"""
[2단계] 엔진 점검: 계산이 맞는지 12개 테스트로 확인하고, 사용 예시를 출력한다.
실행:  python scripts/03_check_engine.py          (project 폴더에서)
모든 테스트가 PASS여야 3단계(앱)로 넘어간다.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shift_engine import ShiftEngine, trading_hours, clock_to_trading

CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"
E = ShiftEngine(CLEAN)
results = []
def check(name, cond, detail=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

# T1 거래시간 변환: 19시~20시 = 거래시간 20, 자정을 넘으면 이어짐
check("T1 시각 변환", clock_to_trading(19) == 20 and trading_hours(23, 2) == [24, 1], f"{trading_hours(23,2)}")
# T2 1단계 결과와 같은가: 연평균 시간별 값(최저 13=387.0, 최고 21=429.5)
h = E.hourly_ci()
check("T2 시간별 최저·최고", h.idxmin() == 13 and h.idxmax() == 21 and abs(h.loc[13]-387.0) < .1 and abs(h.loc[21]-429.5) < .1, f"13시:{h.loc[13]:.1f} 21시:{h.loc[21]:.1f}")
# T3 정오 388.9, 저녁 429.3, 이동분 기준 감소율 9.4%
d = E.denominators(0.1)
check("T3 정오·저녁·감소율", abs(d["noon_ci"]-388.9) < .1 and abs(d["eve_ci"]-429.3) < .1 and abs(d["moved_rate"]-0.0941) < .0005,
      f"정오 {d['noon_ci']:.1f} 저녁 {d['eve_ci']:.1f} (가){d['moved_rate']*100:.2f}%")
# T4 분모 3가지가 02 스크립트 결과(shift_denominators.csv)와 같은가 (연간 + 봄 평일)
sd = pd.read_csv(CLEAN / "shift_denominators.csv"); ok = True
for scope, kw in [("연간", {}), ("봄 평일", dict(season="봄", day_type="평일"))]:
    for p in (10, 20, 30):
        row = sd[(sd.scope == scope) & (sd.p_pct == p)].iloc[0]; x = E.denominators(p/100, **kw)
        ok &= abs(x["moved_rate"]*100-row.moved_pct) < .01 and abs(x["evening_rate"]*100-row.evening_pct) < .01
        ok &= abs(x["daily_rate_market"]*100-row.daily_actual_pct) < .01 and abs(x["daily_rate_uniform"]*100-row.daily_uniform_pct) < .01
check("T4 분모 3가지 = 02 스크립트 결과", ok)
# T5 전력량 보존: 옮기기만 하므로 전후 kWh가 같다
r = E.shift(10, 19, 12, 2)
check("T5 전력량 보존", r["kwh_before"] == r["kwh_after"] == 10)
# T6 되돌리기 대칭: 옮겼다가 되돌리면 감소량의 부호만 바뀐다
a, b = E.shift(5, 19, 12, 2), E.shift(5, 12, 19, 2)
check("T6 대칭", abs(a["saved_g"] + b["saved_g"]) < 1e-9, f"{a['saved_g']:.2f} / {b['saved_g']:.2f}")
# T7 같은 시각으로 옮기면 감소 0
check("T7 같은 시각 = 0", abs(E.shift(3, 14, 14, 1)["saved_g"]) < 1e-9)
# T8 계수 세트 순서: 최소 <= 중앙 <= 최대 (24시간 모두)
hm = [E.hourly_ci(scenario=s) for s in ("min", "mid", "max")]
check("T8 최소<=중앙<=최대", bool(((hm[0] <= hm[1]) & (hm[1] <= hm[2])).all()))
# T9 손계산 대조: 2025-04-15 평일 13~14시(거래시간 14)의 탄소집약도 = 308.372 (손계산 308.4)
check("T9 손계산 대조", abs(E.ci_at("2025-04-15", 13) - 308.372) < .01, f"{E.ci_at('2025-04-15', 13):.3f}")
# T10 잘못된 입력은 오류를 낸다
errs = 0
for f in (lambda: E.shift(-1, 19, 12), lambda: E.window_ci(24, 1), lambda: E.window_ci(10, 0), lambda: E.hourly_ci(season="봄봄")):
    try: f()
    except ValueError: errs += 1
check("T10 잘못된 입력 오류", errs == 4, f"{errs}/4")
# T11 날짜별 분포: 365일, 중앙값 약 9.5%, 상위 10% 약 21.5%
dd = E.daily_distribution()
check("T11 날짜별 분포", len(dd) == 365 and abs(dd.median()-9.53) < .05 and abs(dd.quantile(.9)-21.5) < .1, f"중앙 {dd.median():.2f} 상위10% {dd.quantile(.9):.2f}")
# T12 가장 깨끗한 시작 시각 순위가 허용 범위 안이고, 기준 시각(19시)보다 나쁘지 않다
bs = E.best_start(duration=2, season="봄", day_type="평일")
check("T12 가장 깨끗한 시각", bs.start.min() >= 7 and bs.end.max() <= 22 and bs.saved_rate_vs_ref.iloc[0] >= 0, f"1위 {int(bs.start.iloc[0])}~{int(bs.end.iloc[0])}시")

# T13 엔진 안의 두 계산이 서로 맞는가: shift()의 1kWh 감소량 = denominators()의 격차(g/kWh)
gap = E.denominators(0.1)["gap_g_per_kwh"]; one = E.shift(1, 19, 12, 2)["saved_g"]
check("T13 shift = denominators 일관성", abs(one - gap) < 0.5, f"shift {one:.2f} g / 격차 {gap:.2f} g")
# T14 시간별 값의 가중평균이 연평균(414.894)과 같은가: 시간별 조회가 거래량 가중평균이라는 증거
t = E._table(); wavg = (t["ci_mid"] * t["mwh"]).sum() / t["mwh"].sum()
check("T14 시간별 가중평균 = 연평균", abs(wavg - 414.894) < 0.05, f"{wavg:.3f}")

print(f"\n결과: {sum(results)}/{len(results)} 통과")

# ------------------------------------------------------------------ 사용 예시
print("\n[예시 1] 1kWh를 19시→12시로 2시간 활동 이동 (계수 세트별)")
print(E.shift_band(1, 19, 12, 2).round(3).to_string(index=False))
print("\n[예시 2] 계절x평일/휴일: 1kWh, 19시→12시, 2시간")
rows = []
for s in ["봄", "여름", "가을", "겨울"]:
    for dt in ["평일", "휴일"]:
        r = E.shift(1, 19, 12, 2, s, dt); rows.append(dict(계절=s, 구분=dt, 감소g=r["saved_g"], 감소율=r["saved_rate"]))
print(pd.DataFrame(rows).round(3).to_string(index=False))
print("\n[예시 3] 봄 평일, 2시간 활동 가장 깨끗한 시작 시각 상위 3 (07~22시 안)")
print(E.best_start(2, season="봄", day_type="평일").head(3).round(3).to_string(index=False))
print("\n[예시 4] 라벨 CO2 대표값 (환산계수 미정이라 kWh는 None)")
for c in ["전기세탁기(일반)", "의류건조기"]:
    print(E.activity_defaults(c))
sys.exit(0 if all(results) else 1)
