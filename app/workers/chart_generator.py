"""Pure-Python SVG chart generator.

All functions return complete <svg> strings. No external dependencies.
Colors are passed as hex strings. No CSS variables — SVG is served standalone.
No base64 encoding — use svg_to_file() to get bytes for GCS upload.
"""

from datetime import date
from typing import Callable, List, Optional


def normalize_series(values: List[Optional[float]], strategy: str) -> List[float]:
    """
    Handle None values before charting.

    strategy="zero"        — replace None with 0; used for event counts
                             (jobs_created, jobs_expired, jobs_reposted) where
                             a gap genuinely means zero activity that day.
    strategy="interpolate" — linear interpolation between known values; used for
                             snapshot metrics (jobs_active, avg_salary_eur,
                             median_salary_eur, remote_ratio) where a gap means
                             no snapshot, not zero.

    Edge cases:
    - All values None  → returns list of zeros regardless of strategy.
    - Single data point → value repeated (avoids div-by-zero downstream).
    - All values equal  → flat series; build_polyline renders midline, no crash.
    """
    if all(v is None for v in values):
        return [0.0] * len(values)

    if strategy == "zero":
        return [float(v) if v is not None else 0.0 for v in values]

    # strategy == "interpolate"
    result: List[Optional[float]] = [float(v) if v is not None else None for v in values]

    first_known = next((i for i, v in enumerate(result) if v is not None), None)
    if first_known is None:
        return [0.0] * len(values)

    last_known = next((i for i, v in enumerate(reversed(result)) if v is not None), None)
    last_known = len(result) - 1 - last_known  # type: ignore[operator]

    # Fill leading Nones with first known value
    for i in range(first_known):
        result[i] = result[first_known]

    # Fill trailing Nones with last known value
    for i in range(last_known + 1, len(result)):
        result[i] = result[last_known]

    # Linear interpolation for internal gaps
    i = 0
    while i < len(result):
        if result[i] is None:
            j = i + 1
            while j < len(result) and result[j] is None:
                j += 1
            left_val = result[i - 1]
            right_val = result[j] if j < len(result) else result[i - 1]
            span = j - (i - 1)
            for k in range(i, j):
                t = (k - (i - 1)) / span
                result[k] = left_val + t * (right_val - left_val)  # type: ignore[operator]
            i = j
        else:
            i += 1

    return [float(v) for v in result]  # type: ignore[arg-type]


def build_polyline(
    values: List[float],
    x_start: float,
    x_end: float,
    y_top: float,
    y_bottom: float,
) -> str:
    """
    Map float values to SVG coordinate space.
    Returns a `points` attribute string for <polyline>.

    All coordinates fall within [x_start, x_end] × [y_top, y_bottom].
    Flat series (all values equal) renders as a horizontal midline.
    """
    if not values:
        return ""

    n = len(values)
    min_v = min(values)
    max_v = max(values)
    v_range = max_v - min_v

    points = []
    for i, v in enumerate(values):
        x = x_start if n == 1 else x_start + (i / (n - 1)) * (x_end - x_start)
        if v_range == 0:
            y = (y_top + y_bottom) / 2
        else:
            y = y_bottom - ((v - min_v) / v_range) * (y_bottom - y_top)
        points.append(f"{x:.2f},{y:.2f}")

    return " ".join(points)


def render_x_labels(
    dates: List[date],
    x_start: float,
    x_end: float,
    y: float,
    max_labels: int = 6,
) -> str:
    """
    Generates SVG <text> elements for the x-axis.
    Selects evenly spaced indices to prevent overlap at 30-day density.
    Never emits more than max_labels elements.
    """
    n = len(dates)
    if n == 0:
        return ""

    if n <= max_labels:
        indices = list(range(n))
    else:
        indices = [round(i * (n - 1) / (max_labels - 1)) for i in range(max_labels)]
        indices = sorted(set(indices))

    parts = []
    for i in indices:
        x = x_start if n == 1 else x_start + (i / (n - 1)) * (x_end - x_start)
        label = dates[i].strftime("%b %d")
        parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle"'
            f' font-size="11" font-family="system-ui, sans-serif" fill="#9898a8">{label}</text>'
        )
    return "\n".join(parts)


def generate_sparkline(
    values: List[Optional[float]],
    dates: List[date],
    color: str,
    width: int = 560,
    height: int = 80,
) -> str:
    """
    Minimal chart: polyline + shaded area beneath. No axes, no labels.
    Used for remote_ratio which needs no numeric y-axis to be interpretable.
    Returns a complete <svg> string.
    """
    pad_l, pad_r, pad_t, pad_b = 10, 10, 10, 10
    x_start = float(pad_l)
    x_end = float(width - pad_r)
    y_top = float(pad_t)
    y_bottom = float(height - pad_b)

    normalized = normalize_series(values, "interpolate")
    points_str = build_polyline(normalized, x_start, x_end, y_top, y_bottom)

    if not points_str:
        return (
            f'<svg viewBox="0 0 {width} {height}" width="100%" role="img"'
            f' aria-label="Remote ratio over time"'
            f' xmlns="http://www.w3.org/2000/svg"></svg>'
        )

    first_x = points_str.split(" ")[0].split(",")[0]
    last_x = points_str.split(" ")[-1].split(",")[0]
    area_d = f"M{first_x},{y_bottom:.2f} L{' L'.join(points_str.split(' '))} L{last_x},{y_bottom:.2f} Z"

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img"'
        f' aria-label="Remote ratio over time"'
        f' xmlns="http://www.w3.org/2000/svg"'
        f' font-family="system-ui, sans-serif">\n'
        f"  <defs>\n"
        f'    <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">\n'
        f'      <stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>\n'
        f'      <stop offset="100%" stop-color="{color}" stop-opacity="0.03"/>\n'
        f"    </linearGradient>\n"
        f"  </defs>\n"
        f'  <path d="{area_d}" fill="url(#sg)"/>\n'
        f'  <polyline fill="none" stroke="{color}" stroke-width="1.5" points="{points_str}"/>\n'
        f"</svg>"
    )


def generate_line_chart(
    values: List[Optional[float]],
    dates: List[date],
    color: str,
    y_label: Callable[[float], str],
    width: int = 560,
    height: int = 160,
) -> str:
    """
    Full chart: polyline + y-axis with 3 gridlines + y-tick labels + x-axis dates.
    y_label: callable to format y-axis tick values, e.g. lambda v: f"€{int(v):,}"
    Suitable for jobs_active (count) and salary series (EUR values).
    Returns a complete <svg> string.
    """
    pad_l, pad_r, pad_t, pad_b = 62, 15, 12, 30
    x_start = float(pad_l)
    x_end = float(width - pad_r)
    y_top = float(pad_t)
    y_bottom = float(height - pad_b)

    all_none = all(v is None for v in values)
    normalized = normalize_series(values, "interpolate")
    points_str = build_polyline(normalized, x_start, x_end, y_top, y_bottom)

    min_v = min(normalized) if normalized else 0.0
    max_v = max(normalized) if normalized else 0.0

    gridlines_parts = []
    for gy, gv in [
        (y_top, max_v),
        ((y_top + y_bottom) / 2, (max_v + min_v) / 2),
        (y_bottom, min_v),
    ]:
        gridlines_parts.append(
            f'  <line x1="{x_start:.2f}" y1="{gy:.2f}" x2="{x_end:.2f}" y2="{gy:.2f}"'
            f' stroke="#ddddd4" stroke-width="1"/>'
        )
        gridlines_parts.append(
            f'  <text x="{x_start - 5:.2f}" y="{gy + 4:.2f}" text-anchor="end"'
            f' font-size="11" font-family="system-ui, sans-serif"'
            f' fill="#9898a8">{y_label(gv)}</text>'
        )

    x_labels = render_x_labels(dates, x_start, x_end, y_bottom + 15)

    no_data = ""
    if all_none:
        cx = (x_start + x_end) / 2
        cy = (y_top + y_bottom) / 2
        no_data = (
            f'  <text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle"'
            f' font-size="13" font-family="system-ui, sans-serif"'
            f' fill="#9898a8">No data available</text>\n'
        )

    polyline = (
        f'  <polyline fill="none" stroke="{color}" stroke-width="1.5" points="{points_str}"/>\n' if points_str else ""
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img"'
        f' aria-label="Chart over time"'
        f' xmlns="http://www.w3.org/2000/svg"'
        f' font-family="system-ui, sans-serif">\n'
        + "\n".join(gridlines_parts)
        + "\n"
        + polyline
        + (x_labels + "\n" if x_labels else "")
        + no_data
        + "</svg>"
    )


def generate_volume_chart(
    created: List[Optional[float]],
    expired: List[Optional[float]],
    active: List[Optional[float]],
    dates: List[date],
    width: int = 560,
    height: int = 160,
) -> str:
    """
    Three polylines on a shared y-axis:
      created = blue (#3B82F6)
      expired = red  (#EF4444)
      active  = gray (#6B7280)
    Returns a complete <svg> string.
    """
    pad_l, pad_r, pad_t, pad_b = 62, 15, 12, 30
    x_start = float(pad_l)
    x_end = float(width - pad_r)
    y_top = float(pad_t)
    y_bottom = float(height - pad_b)

    norm_created = normalize_series(created, "zero")
    norm_expired = normalize_series(expired, "zero")
    norm_active = normalize_series(active, "interpolate")

    all_values = norm_created + norm_expired + norm_active
    global_min = min(all_values) if all_values else 0.0
    global_max = max(all_values) if all_values else 0.0
    v_range = global_max - global_min

    def _map(vals: List[float]) -> str:
        n = len(vals)
        pts = []
        for i, v in enumerate(vals):
            x = x_start if n <= 1 else x_start + (i / (n - 1)) * (x_end - x_start)
            y = (
                (y_top + y_bottom) / 2
                if v_range == 0
                else (y_bottom - ((v - global_min) / v_range) * (y_bottom - y_top))
            )
            pts.append(f"{x:.2f},{y:.2f}")
        return " ".join(pts)

    pts_created = _map(norm_created)
    pts_expired = _map(norm_expired)
    pts_active = _map(norm_active)

    gridlines_parts = []
    for gy, gv in [
        (y_top, global_max),
        ((y_top + y_bottom) / 2, (global_max + global_min) / 2),
        (y_bottom, global_min),
    ]:
        gridlines_parts.append(
            f'  <line x1="{x_start:.2f}" y1="{gy:.2f}" x2="{x_end:.2f}" y2="{gy:.2f}"'
            f' stroke="#ddddd4" stroke-width="1"/>'
        )
        gridlines_parts.append(
            f'  <text x="{x_start - 5:.2f}" y="{gy + 4:.2f}" text-anchor="end"'
            f' font-size="11" font-family="system-ui, sans-serif"'
            f' fill="#9898a8">{int(gv)}</text>'
        )

    x_labels = render_x_labels(dates, x_start, x_end, y_bottom + 15)

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img"'
        f' aria-label="Job volume over time"'
        f' xmlns="http://www.w3.org/2000/svg"'
        f' font-family="system-ui, sans-serif">\n'
        + "\n".join(gridlines_parts)
        + "\n"
        + f'  <polyline fill="none" stroke="#3B82F6" stroke-width="1.5" points="{pts_created}"/>\n'
        + f'  <polyline fill="none" stroke="#EF4444" stroke-width="1.5" points="{pts_expired}"/>\n'
        + f'  <polyline fill="none" stroke="#6B7280" stroke-width="1.5" points="{pts_active}"/>\n'
        + (x_labels + "\n" if x_labels else "")
        + "</svg>"
    )


def svg_to_file(svg_str: str) -> bytes:
    """Encode SVG string to UTF-8 bytes for GCS upload. No base64."""
    return svg_str.encode("utf-8")
