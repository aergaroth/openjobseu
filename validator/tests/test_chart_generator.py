import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pytest

from app.workers.chart_generator import (
    build_polyline,
    generate_line_chart,
    generate_sparkline,
    generate_volume_chart,
    normalize_series,
    render_x_labels,
)

_today = date.today()
_dates_30 = [_today - timedelta(days=29 - i) for i in range(30)]
_dates_7 = _dates_30[-7:]


def test_normalize_series_interpolate():
    values = [10.0, None, None, 40.0]
    result = normalize_series(values, "interpolate")
    assert result[0] == pytest.approx(10.0)
    assert result[3] == pytest.approx(40.0)
    assert result[1] == pytest.approx(20.0)
    assert result[2] == pytest.approx(30.0)


def test_normalize_series_zero():
    values = [10.0, None, 30.0]
    result = normalize_series(values, "zero")
    assert result == [10.0, 0.0, 30.0]


def test_normalize_all_none():
    values = [None, None, None]
    assert normalize_series(values, "zero") == [0.0, 0.0, 0.0]
    assert normalize_series(values, "interpolate") == [0.0, 0.0, 0.0]


def test_normalize_single_point():
    assert normalize_series([42.0], "zero") == [42.0]
    assert normalize_series([42.0], "interpolate") == [42.0]


def test_normalize_all_equal():
    values = [5.0, 5.0, 5.0]
    assert normalize_series(values, "zero") == [5.0, 5.0, 5.0]
    assert normalize_series(values, "interpolate") == [5.0, 5.0, 5.0]


def test_build_polyline_bounds():
    values = [10.0, 20.0, 15.0, 30.0, 5.0]
    x_start, x_end, y_top, y_bottom = 55.0, 545.0, 10.0, 95.0
    points_str = build_polyline(values, x_start, x_end, y_top, y_bottom)
    assert points_str
    for point in points_str.split(" "):
        x, y = map(float, point.split(","))
        assert x_start <= x <= x_end, f"x={x} out of bounds [{x_start}, {x_end}]"
        assert y_top <= y <= y_bottom, f"y={y} out of bounds [{y_top}, {y_bottom}]"


def test_render_x_labels_max():
    max_labels = 4
    labels_svg = render_x_labels(_dates_30, 55.0, 545.0, 110.0, max_labels=max_labels)
    assert labels_svg.count("<text") <= max_labels


def test_generate_line_chart_returns_valid_svg():
    values = [100.0, 200.0, None, 150.0, 180.0]
    chart = generate_line_chart(values, _dates_7[:5], "#4A90E2", lambda v: f"{int(v)}")
    assert "<svg" in chart
    ET.fromstring(chart)  # raises if not valid XML


def test_generate_volume_chart_three_polylines():
    created = [10, 12, 8, 15, 11, 9, 13]
    expired = [5, 6, 4, 7, 5, 4, 6]
    active = [100, 106, 110, 118, 124, 129, 136]
    chart = generate_volume_chart(created, expired, active, _dates_7)
    assert chart.count("<polyline") == 3


def test_generate_sparkline_no_axes():
    values = [0.5, 0.6, None, 0.7, 0.65]
    chart = generate_sparkline(values, _dates_7[:5], "#F5A623")
    assert "<text" not in chart


def test_svg_has_aria_label():
    values = [10.0, 20.0, 30.0]
    dates = _dates_7[:3]
    assert "aria-label" in generate_sparkline(values, dates, "#F5A623")
    assert "aria-label" in generate_line_chart(values, dates, "#4A90E2", lambda v: f"{int(v)}")
    assert "aria-label" in generate_volume_chart(values, values, values, dates)
