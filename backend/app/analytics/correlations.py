from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass
class CorrelatedPair:
    entity_a: str
    entity_b: str
    correlation: float
    p_value: float | None = None
    common_years: int = 0
    description: str = ""


def compute_correlations(
    time_series_map: dict[str, dict[int, float]],
    min_common_years: int = 3,
) -> list[CorrelatedPair]:
    keys = list(time_series_map.keys())
    results: list[CorrelatedPair] = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a = time_series_map[keys[i]]
            b = time_series_map[keys[j]]
            common_years = sorted(set(a.keys()) & set(b.keys()))
            if len(common_years) < min_common_years:
                continue
            a_vals = [a[y] for y in common_years]
            b_vals = [b[y] for y in common_years]
            r = _pearson_r(a_vals, b_vals)
            results.append(CorrelatedPair(
                entity_a=keys[i],
                entity_b=keys[j],
                correlation=round(r, 4),
                common_years=len(common_years),
            ))
    results.sort(key=lambda x: abs(x.correlation), reverse=True)
    return results


def correlate_alerts_with_consumption(
    alert_years: dict[int, int],
    consumption_series: dict[str, dict[int, float]],
    window_years: int = 2,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entity_key, year_values in consumption_series.items():
        sorted_years = sorted(year_values.keys())
        if len(sorted_years) < 4:
            continue
        overall_mean = mean(year_values.values())
        before_means = []
        after_means = []
        for alert_year, count in alert_years.items():
            before_vals = [
                year_values[y] for y in sorted_years
                if alert_year - window_years <= y < alert_year
            ]
            after_vals = [
                year_values[y] for y in sorted_years
                if alert_year < y <= alert_year + window_years
            ]
            if before_vals and after_vals:
                before_means.append(mean(before_vals))
                after_means.append(mean(after_vals))
        if before_means and after_means:
            avg_before = mean(before_means)
            avg_after = mean(after_means)
            change_pct = ((avg_after - avg_before) / avg_before * 100) if avg_before != 0 else 0
            results.append({
                "entity_key": entity_key,
                "avg_before": round(avg_before, 4),
                "avg_after": round(avg_after, 4),
                "change_pct": round(change_pct, 2),
                "direction": "increased" if change_pct > 0 else "decreased",
                "overall_mean": round(overall_mean, 4),
            })
    return sorted(results, key=lambda x: abs(x["change_pct"]), reverse=True)


def _pearson_r(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    x_mean = mean(x)
    y_mean = mean(y)
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    x_std = (sum((xi - x_mean) ** 2 for xi in x)) ** 0.5
    y_std = (sum((yi - y_mean) ** 2 for yi in y)) ** 0.5
    denominator = x_std * y_std
    if denominator == 0:
        return 0.0
    return numerator / denominator
