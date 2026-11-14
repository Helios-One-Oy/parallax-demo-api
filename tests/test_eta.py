from datetime import datetime, timezone

import pytest

from northbound_api.eta import (
    Service,
    add_working_days,
    dispatch_day,
    distance_km,
    estimate,
    lane,
    transit_days,
)
from northbound_api.hubs import UnknownHub, get_hub

HEL, TLL, OUL, TMP, TOS = (get_hub(c) for c in ("HEL", "TLL", "OUL", "TMP", "TOS"))


def utc(y, m, d, h=9):
    return datetime(y, m, d, h, 0, tzinfo=timezone.utc)


def test_distance_helsinki_tallinn_is_about_82_km():
    assert distance_km(HEL, TLL) == pytest.approx(82, abs=3)


def test_distance_is_symmetric_and_zero_to_itself():
    assert distance_km(HEL, OUL) == pytest.approx(distance_km(OUL, HEL))
    assert distance_km(HEL, HEL) == 0


def test_lane_marks_border_crossings():
    assert lane(HEL, TLL).cross_border is True
    assert lane(HEL, TMP).cross_border is False


def test_lane_to_the_same_hub_is_rejected():
    with pytest.raises(ValueError):
        lane(HEL, HEL)


def test_unknown_hub():
    with pytest.raises(UnknownHub):
        get_hub("XXX")
    assert get_hub("hel") is HEL


def test_slower_service_never_takes_fewer_days():
    for dest in (TLL, OUL, TMP, TOS):
        ln = lane(HEL, dest)
        days = [transit_days(ln, s) for s in (Service.express, Service.standard, Service.economy)]
        assert days == sorted(days)
        assert days[0] >= 1


def test_border_adds_one_day():
    # Helsinki to Tallinn is a short hop: one day on the road plus one for the border.
    assert transit_days(lane(HEL, TLL), Service.express) == 2
    assert transit_days(lane(HEL, TMP), Service.express) == 1


def test_pickup_before_cutoff_leaves_the_same_day():
    assert dispatch_day(utc(2026, 11, 9, 9)).date().isoformat() == "2026-11-09"  # a Monday


def test_pickup_after_cutoff_leaves_the_next_working_day():
    assert dispatch_day(utc(2026, 11, 9, 15)).date().isoformat() == "2026-11-10"
    # Friday afternoon rolls over the weekend.
    assert dispatch_day(utc(2026, 11, 13, 15)).date().isoformat() == "2026-11-16"


def test_weekend_pickup_leaves_on_monday():
    assert dispatch_day(utc(2026, 11, 14)).date().isoformat() == "2026-11-16"
    assert dispatch_day(utc(2026, 11, 15)).date().isoformat() == "2026-11-16"


def test_working_days_skip_the_weekend():
    friday = utc(2026, 11, 13, 0)
    assert add_working_days(friday, 1).date().isoformat() == "2026-11-16"
    assert add_working_days(friday, 6).date().isoformat() == "2026-11-23"


def test_estimate_window_for_a_domestic_express_parcel():
    w = estimate(HEL, TMP, Service.express, utc(2026, 11, 12, 9))  # Thursday morning
    assert w.transit_days == 1
    assert w.eta_start == datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    assert w.eta_end == datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)


def test_estimate_window_widens_for_economy():
    express = estimate(HEL, OUL, Service.express, utc(2026, 11, 9))
    economy = estimate(HEL, OUL, Service.economy, utc(2026, 11, 9))
    assert economy.eta_start >= express.eta_start
    assert (economy.eta_end - economy.eta_start) > (express.eta_end - express.eta_start)
    assert economy.eta_start.weekday() < 5 and economy.eta_end.weekday() < 5


def test_estimate_needs_a_time_zone():
    with pytest.raises(ValueError):
        estimate(HEL, OUL, Service.standard, datetime(2026, 11, 9, 9, 0))
