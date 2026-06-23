from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any


@dataclass
class TrendResult:
    entity_key: str
    metric: str
    years: list[int]
    values: list[float]
    slope: float = 0.0
    mean_value: float = 0.0
    stdev_value: float = 0.0
    total_change: float = 0.0
    avg_yoy_change: float = 0.0
    start_value: float | None = None
    end_value: float | None = None
    trend_direction: str = "stable"
    alerts_count: int = 0
    geography: str = ""


def compute_trend_analysis(
    time_series: dict[str, dict[int, float]],
    metric: str = "dhd",
    geography: str = "",
) -> list[TrendResult]:
    results: list[TrendResult] = []
    for entity_key, year_values in time_series.items():
        if len(year_values) < 2:
            continue
        sorted_years = sorted(year_values.keys())
        sorted_values = [year_values[y] for y in sorted_years]

        n = len(sorted_years)
        if n < 2:
            continue

        x_mean = mean(sorted_years)
        y_mean = mean(sorted_values)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(sorted_years, sorted_values))
        denominator = sum((x - x_mean) ** 2 for x in sorted_years)
        slope = numerator / denominator if denominator != 0 else 0.0

        start_val = sorted_values[0]
        end_val = sorted_values[-1]
        total_change = end_val - start_val if start_val != 0 else 0.0

        yoy_changes = []
        for i in range(1, n):
            if sorted_values[i - 1] != 0:
                yoy_changes.append((sorted_values[i] - sorted_values[i - 1]) / abs(sorted_values[i - 1]) * 100)
        avg_yoy = mean(yoy_changes) if yoy_changes else 0.0

        if slope > 0.01:
            direction = "increasing"
        elif slope < -0.01:
            direction = "decreasing"
        else:
            direction = "stable"

        results.append(TrendResult(
            entity_key=entity_key,
            metric=metric,
            years=sorted_years,
            values=[round(v, 4) for v in sorted_values],
            slope=round(slope, 6),
            mean_value=round(y_mean, 4),
            stdev_value=round(stdev(sorted_values), 4) if len(sorted_values) > 1 else 0.0,
            total_change=round(total_change, 4),
            avg_yoy_change=round(avg_yoy, 2),
            start_value=start_val,
            end_value=end_val,
            trend_direction=direction,
            geography=geography,
        ))
    return results


def compute_year_over_year(
    time_series: dict[str, dict[int, float]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entity_key, year_values in time_series.items():
        sorted_years = sorted(year_values.keys())
        for i in range(1, len(sorted_years)):
            prev_year = sorted_years[i - 1]
            curr_year = sorted_years[i]
            prev_val = year_values[prev_year]
            curr_val = year_values[curr_year]
            if prev_val == 0:
                continue
            change_pct = round((curr_val - prev_val) / prev_val * 100, 2)
            results.append({
                "entity_key": entity_key,
                "year": curr_year,
                "previous_year": prev_year,
                "value": round(curr_val, 4),
                "previous_value": round(prev_val, 4),
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat"),
            })
    return results


def detect_trend_changes(
    time_series: dict[str, dict[int, float]],
    change_threshold: float = 20.0,
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for entity_key, year_values in time_series.items():
        sorted_years = sorted(year_values.keys())
        for i in range(1, len(sorted_years)):
            prev_year = sorted_years[i - 1]
            curr_year = sorted_years[i]
            prev_val = year_values[prev_year]
            curr_val = year_values[curr_year]
            if prev_val == 0:
                continue
            change_pct = abs((curr_val - prev_val) / prev_val * 100)
            if change_pct >= change_threshold:
                anomalies.append({
                    "entity_key": entity_key,
                    "year": curr_year,
                    "previous_year": prev_year,
                    "value": round(curr_val, 4),
                    "previous_value": round(prev_val, 4),
                    "change_pct": round(change_pct, 2),
                    "direction": "spike" if curr_val > prev_val else "drop",
                })
    return sorted(anomalies, key=lambda x: x["change_pct"], reverse=True)
