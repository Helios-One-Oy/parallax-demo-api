"""Lane distances and delivery windows.

The model is deliberately simple: great-circle distance between hubs, a detour
factor for roads, a daily line-haul range per service level, one extra day when
a lane crosses a border, and no movement on Saturdays and Sundays. Public
holidays are not modelled.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from math import asin, ceil, cos, radians, sin, sqrt

from .hubs import Hub

EARTH_RADIUS_KM = 6371.0088
ROAD_DETOUR_FACTOR = 1.25
CUTOFF_HOUR_UTC = 14  # parcels handed in later leave on the next working day
WINDOW_OPENS = time(8, 0)
WINDOW_CLOSES = time(18, 0)


class Service(str, Enum):
    express = "express"
    standard = "standard"
    economy = "economy"


# Line-haul range in road kilometres per working day.
DAILY_RANGE_KM = {Service.express: 900, Service.standard: 550, Service.economy: 350}
# Working days of slack between the earliest and the latest delivery day.
WINDOW_SLACK_DAYS = {Service.express: 0, Service.standard: 1, Service.economy: 2}


@dataclass(frozen=True)
class Lane:
    origin: Hub
    destination: Hub
    distance_km: float
    road_km: float
    cross_border: bool


@dataclass(frozen=True)
class EtaWindow:
    lane: Lane
    service: Service
    transit_days: int
    dispatch_day: datetime
    eta_start: datetime
    eta_end: datetime


def distance_km(a: Hub, b: Hub) -> float:
    """Great-circle distance between two hubs (haversine)."""
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def lane(origin: Hub, destination: Hub) -> Lane:
    if origin.code == destination.code:
        raise ValueError("origin and destination are the same hub")
    d = distance_km(origin, destination)
    return Lane(
        origin=origin,
        destination=destination,
        distance_km=round(d, 1),
        road_km=round(d * ROAD_DETOUR_FACTOR, 1),
        cross_border=origin.country != destination.country,
    )


def transit_days(ln: Lane, service: Service) -> int:
    """Working days on the road, at least one, plus one for a border crossing."""
    days = max(1, ceil(ln.road_km / DAILY_RANGE_KM[service]))
    return days + (1 if ln.cross_border else 0)


def is_working_day(d: datetime) -> bool:
    return d.weekday() < 5


def next_working_day(d: datetime) -> datetime:
    d += timedelta(days=1)
    while not is_working_day(d):
        d += timedelta(days=1)
    return d


def add_working_days(d: datetime, days: int) -> datetime:
    for _ in range(days):
        d = next_working_day(d)
    return d


def dispatch_day(pickup: datetime) -> datetime:
    """The working day the parcel leaves the origin hub (midnight UTC of that day)."""
    pickup = pickup.astimezone(timezone.utc)
    day = pickup.replace(hour=0, minute=0, second=0, microsecond=0)
    if not is_working_day(day):
        return next_working_day(day)
    if pickup.hour >= CUTOFF_HOUR_UTC:
        return next_working_day(day)
    return day


def estimate(origin: Hub, destination: Hub, service: Service, pickup: datetime) -> EtaWindow:
    if pickup.tzinfo is None:
        raise ValueError("pickup must carry a time zone")
    ln = lane(origin, destination)
    days = transit_days(ln, service)
    start_day = dispatch_day(pickup)
    first = add_working_days(start_day, days)
    last = add_working_days(first, WINDOW_SLACK_DAYS[service])
    return EtaWindow(
        lane=ln,
        service=service,
        transit_days=days,
        dispatch_day=start_day,
        eta_start=datetime.combine(first.date(), WINDOW_OPENS, tzinfo=timezone.utc),
        eta_end=datetime.combine(last.date(), WINDOW_CLOSES, tzinfo=timezone.utc),
    )
