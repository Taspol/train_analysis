import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import live_view


class TestIsFilled:
    @pytest.mark.parametrize("value,expected", [
        (None, False),
        ("", False),
        ("   ", False),
        ("-", False),
        ("0", False),
        ("None", False),
        ("17:30", True),
        ("ยะลา", True),
        (0, True),
        (1, True),
    ])
    def test_cases(self, value, expected):
        assert live_view._is_filled(value) is expected


class TestCoerceInt:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("", None),
        ("-", None),
        ("28", 28),
        (28, 28),
        (28.7, 28),
        ("28.0", 28),
        ("not a number", None),
    ])
    def test_cases(self, value, expected):
        assert live_view._coerce_int(value) == expected


class TestStatusColor:
    def test_unknown_when_none(self):
        label, color = live_view._status_color(None)
        assert label == "Unknown"

    def test_on_time_for_small_delay(self):
        label, _ = live_view._status_color(0)
        assert label == "On time"
        assert live_view._status_color(5)[0] == "On time"

    def test_slight_for_mid_delay(self):
        assert live_view._status_color(15)[0] == "Slight delay"
        assert live_view._status_color(30)[0] == "Slight delay"

    def test_major_for_big_delay(self):
        assert live_view._status_color(45)[0] == "Major delay"
        assert live_view._status_color(180)[0] == "Major delay"


class TestHhmmAdd:
    @pytest.mark.parametrize("base,delta,expected", [
        ("17:30", 0, "17:30"),
        ("17:30", 30, "18:00"),
        ("17:30", 45, "18:15"),
        ("23:45", 30, "00:15"),
        ("00:00", 60, "01:00"),
        ("17:30", -10, "17:20"),
    ])
    def test_arithmetic(self, base, delta, expected):
        assert live_view._hhmm_add(base, delta) == expected

    def test_invalid_base_returned_as_is(self):
        assert live_view._hhmm_add("", 10) == ""
        assert live_view._hhmm_add("not-a-time", 10) == "not-a-time"


class TestResolveCurrentIndex:
    def test_no_arrivals_returns_zero(self):
        stations = [{"act_arrtime": ""}, {"act_arrtime": None}]
        assert live_view._resolve_current_index(stations) == 0

    def test_first_station_arrived_not_departed(self):
        stations = [
            {"act_arrtime": "17:00", "act_deptime": ""},
            {"act_arrtime": "", "act_deptime": ""},
        ]
        assert live_view._resolve_current_index(stations) == 0

    def test_advance_when_departed(self):
        stations = [
            {"act_arrtime": "17:00", "act_deptime": "17:30"},
            {"act_arrtime": "", "act_deptime": ""},
        ]
        assert live_view._resolve_current_index(stations) == 1

    def test_last_arrived_is_current_when_terminal(self):
        stations = [
            {"act_arrtime": "17:00", "act_deptime": "17:30"},
            {"act_arrtime": "20:00", "act_deptime": ""},
        ]
        assert live_view._resolve_current_index(stations) == 1

    def test_real_train_169_terminal_complete(self):
        stations = [
            {"act_arrtime": "17:00", "act_deptime": "17:30"},
            {"act_arrtime": "18:30", "act_deptime": "18:32"},
            {"act_arrtime": "06:30", "act_deptime": ""},
        ]
        assert live_view._resolve_current_index(stations) == 2
