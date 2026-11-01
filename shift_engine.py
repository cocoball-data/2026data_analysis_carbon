"""
[2단계] 시간 이동 계산 엔진 (앱의 계산 담당)
- 1단계 결과 CSV(ci_dayhour.csv 등)를 읽어서 '이 전기를 다른 시간으로 옮기면 몇 g이 줄어드는가'를 계산한다.
- 앱(3단계)은 이 파일을 불러와서(import) 쓰기만 한다. 계산 규칙을 한곳에 모아 두는 이유는
  (1) 숫자가 화면마다 달라지는 것을 막고 (2) 테스트로 계산이 맞는지 확인하기 위해서이다.

세 부분으로 읽으면 된다.
  Part 1. 시간 규칙 : 시계 시각 <-> 거래시간 변환
  Part 2. 탄소집약도 조회 : 계절·평일/휴일·월·계수 세트로 시간별 값을 구함
  Part 3. 이동 계산 : 활동 1건의 감소량(g), 감소율 3가지 분모, 가장 깨끗한 시작 시각
"""
from pathlib import Path
import numpy as np
import pandas as pd

SCENARIOS = {"mid": "ci_mid", "min": "ci_min", "max": "ci_max", "direct": "ci_direct"}
SCENARIO_LABEL = {"mid": "IPCC 전과정 중앙값(기본)", "min": "IPCC 전과정 최소", "max": "IPCC 전과정 최대", "direct": "직접배출"}
EVENING = (19, 2)   # 저녁 19~21시: (시작 시각, 길이)
NOON = (12, 2)      # 정오 12~14시


# =============================================================== Part 1. 시간 규칙
def clock_to_trading(clock_hour: int) -> int:
    """시계 시각(0~23, 그 시각부터 1시간) -> 거래시간(1~24).
    거래시간 h는 (h-1)시~h시 구간이므로, 19시~20시는 거래시간 20이다."""
    if not (0 <= int(clock_hour) <= 23):
        raise ValueError(f"시각은 0~23이어야 함: {clock_hour}")
    return int(clock_hour) + 1


def trading_hours(start_clock: int, duration: int) -> list:
    """start_clock 시작, duration 시간 동안의 거래시간 목록 (자정을 넘으면 0시로 이어짐)."""
    if not (0 <= int(start_clock) <= 23):
        raise ValueError(f"시작 시각은 0~23이어야 함: {start_clock}")
    if not (1 <= int(duration) <= 24):
        raise ValueError(f"길이는 1~24시간이어야 함: {duration}")
    return [clock_to_trading((int(start_clock) + k) % 24) for k in range(int(duration))]


class ShiftEngine:
    def __init__(self, clean_dir):
        clean_dir = Path(clean_dir)
        self.dh = pd.read_csv(clean_dir / "ci_dayhour.csv")
        self.daily = pd.read_csv(clean_dir / "daily_potential.csv")
        self.presets = pd.read_csv(clean_dir / "activity_presets.csv")
        self._cache = {}

    # =========================================================== Part 2. 탄소집약도 조회
    def _table(self, season=None, day_type=None, month=None):
        """거래시간별 (거래량 합, 배출량 합, 탄소집약도) 표. 같은 조건은 한 번만 계산한다."""
        key = (season, day_type, month)
        if key in self._cache:
            return self._cache[key]
        d = self.dh
        if season is not None:   d = d[d.season == season]
        if day_type is not None: d = d[d.day_type == day_type]
        if month is not None:    d = d[d.month == month]
        if d.empty:
            raise ValueError(f"조건에 맞는 자료가 없음: {key}")
        out = pd.DataFrame({"mwh": d.groupby("hour")["total_mwh"].sum()})
        for sc, col in SCENARIOS.items():
            out["em_" + sc] = (d[col] * d["total_mwh"]).groupby(d["hour"]).sum()   # 배출량 = 집약도 x 거래량
            out["ci_" + sc] = out["em_" + sc] / out["mwh"]                         # 가중평균 탄소집약도
        self._cache[key] = out
        return out

    def hourly_ci(self, season=None, day_type=None, month=None, scenario="mid") -> pd.Series:
        """거래시간 1~24별 탄소집약도(gCO2eq/kWh). 조건을 None으로 두면 전체."""
        return self._table(season, day_type, month)["ci_" + scenario]

    def window_ci(self, start_clock, duration=1, season=None, day_type=None, month=None, scenario="mid") -> float:
        """활동이 start_clock부터 duration시간 일정한 전력으로 돌 때의 평균 탄소집약도."""
        ci = self.hourly_ci(season, day_type, month, scenario)
        return float(ci.loc[trading_hours(start_clock, duration)].mean())

    def ci_at(self, date, start_clock, scenario="mid") -> float:
        """특정 날짜의 특정 시각 탄소집약도 (손계산 대조용)."""
        row = self.dh[(self.dh.date == str(date)) & (self.dh.hour == clock_to_trading(start_clock))]
        if row.empty:
            raise ValueError(f"해당 날짜·시각 자료 없음: {date} {start_clock}시")
        return float(row[SCENARIOS[scenario]].iloc[0])

    # =========================================================== Part 3. 이동 계산
    def shift(self, kwh, from_start, to_start, duration=1, season=None, day_type=None, month=None, scenario="mid") -> dict:
        """활동 1건(kwh)을 from_start 시각에서 to_start 시각으로 옮길 때의 결과.
        전력량은 그대로(옮기기만 하고 줄이지 않음)이므로 kwh_before == kwh_after 이다."""
        if kwh < 0:
            raise ValueError("kWh는 0 이상이어야 함")
        ci0 = self.window_ci(from_start, duration, season, day_type, month, scenario)
        ci1 = self.window_ci(to_start, duration, season, day_type, month, scenario)
        before, after = kwh * ci0, kwh * ci1
        saved = before - after
        rate = saved / before if before > 0 else float("nan")
        return dict(kwh_before=kwh, kwh_after=kwh, ci_from=ci0, ci_to=ci1, g_before=before, g_after=after,
                    saved_g=saved, saved_rate=rate,       # 이동분 기준 감소율. '안 쓰고 줄이기' 대비 옮기기의 효과와 같은 값
                    reduce_g=before)                      # 같은 전력을 아예 쓰지 않을 때의 감소량(비교용)

    def shift_band(self, kwh, from_start, to_start, duration=1, season=None, day_type=None, month=None) -> pd.DataFrame:
        """계수 4세트로 같은 이동을 계산해 불확실성 범위를 보여 줌."""
        rows = []
        for sc in SCENARIOS:
            r = self.shift(kwh, from_start, to_start, duration, season, day_type, month, sc)
            rows.append(dict(scenario=SCENARIO_LABEL[sc], ci_from=r["ci_from"], ci_to=r["ci_to"], saved_g=r["saved_g"], saved_rate=r["saved_rate"]))
        return pd.DataFrame(rows)

    def denominators(self, p, season=None, day_type=None, month=None, scenario="mid") -> dict:
        """저녁(19~21시) 사용의 p를 정오(12~14시)로 옮길 때 감소율 3가지 분모 (교수님 피드백).
        (가) 이동한 전력의 원래 배출 (나) 저녁 19~21시 총 배출 (다) 하루 전체 배출"""
        t = self._table(season, day_type, month)
        eh, nh = trading_hours(*EVENING), trading_hours(*NOON)
        eve = t.loc[eh, "em_" + scenario].sum() / t.loc[eh, "mwh"].sum()       # 저녁 가중평균 CI
        noon = t.loc[nh, "em_" + scenario].sum() / t.loc[nh, "mwh"].sum()
        gap = eve - noon
        day_avg = t["em_" + scenario].sum() / t["mwh"].sum()                    # 하루 가중평균 CI
        share_eve = t.loc[eh, "mwh"].sum() / t["mwh"].sum()                     # 저녁이 하루 사용에서 차지하는 비중(시장 거래량 모양)
        uniform = p * (len(eh) / 24) * gap / t["ci_" + scenario].mean()         # 24시간 고르게 쓴다고 가정
        return dict(p=p, noon_ci=noon, eve_ci=eve, gap_g_per_kwh=gap,
                    moved_rate=gap / eve,                                       # (가)
                    evening_rate=p * gap / eve,                                 # (나)
                    daily_rate_market=p * share_eve * gap / day_avg,            # (다) 시장 거래량 모양
                    daily_rate_uniform=uniform,                                 # (다) 고르게 사용
                    evening_share_of_day=share_eve)

    def best_start(self, duration=1, earliest=7, latest_end=22, reference_start=19, season=None, day_type=None,
                   month=None, scenario="mid") -> pd.DataFrame:
        """허용 시간 안(earliest시 이후 시작, latest_end시 이전 종료)에서 가장 깨끗한 시작 시각 순위."""
        rows = []
        ref = self.window_ci(reference_start, duration, season, day_type, month, scenario)
        for s in range(earliest, latest_end - duration + 1):
            c = self.window_ci(s, duration, season, day_type, month, scenario)
            rows.append(dict(start=s, end=s + duration, ci=c, saved_rate_vs_ref=(ref - c) / ref))
        return pd.DataFrame(rows).sort_values("ci").reset_index(drop=True)

    def daily_distribution(self, season=None, day_type=None) -> pd.Series:
        """날짜별 이동분 감소율(저녁->정오, %) 분포. 앱에서 히스토그램으로 보여 줌."""
        d = self.daily
        if season is not None:   d = d[d.season == season]
        if day_type is not None: d = d[d.day_type == day_type]
        return d["red_to_noon_pct"]

    def activity_defaults(self, category, ef_g_per_kwh=None) -> dict:
        """에너지공단 품목의 라벨 CO2(g) 대표값. 환산계수가 있으면 kWh도 계산하고, 없으면 kWh는 None."""
        r = self.presets[self.presets.category == category]
        if r.empty:
            raise ValueError(f"품목 없음: {category}")
        r = r.iloc[0]
        out = dict(category=category, use_unit=str(r.use_unit), co2_label_median=float(r.co2_median), co2_label_p25=float(r.co2_p25), co2_label_p75=float(r.co2_p75))
        out.update({"kwh_median": None, "kwh_p25": None, "kwh_p75": None})
        if ef_g_per_kwh:
            out.update(kwh_median=r.co2_median / ef_g_per_kwh, kwh_p25=r.co2_p25 / ef_g_per_kwh, kwh_p75=r.co2_p75 / ef_g_per_kwh)
        return out
