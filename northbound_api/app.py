"""HTTP API of the Northbound Dispatch ETA service."""

from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from . import __version__
from .eta import Service, estimate, lane, transit_days
from .hubs import HUBS, UnknownHub, get_hub


class ApiModel(BaseModel):
    """JSON in camelCase, the same field style as the web service."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HubOut(ApiModel):
    code: str
    name: str
    country: str


class LaneOut(ApiModel):
    origin: str
    destination: str
    distance_km: float
    road_km: float
    cross_border: bool
    transit_days: dict[Service, int]


class EtaRequest(ApiModel):
    origin: str
    destination: str
    service: Service = Service.standard
    pickup: AwareDatetime


class EtaOut(ApiModel):
    origin: str
    destination: str
    service: Service
    transit_days: int
    dispatch_day: str
    eta_start: datetime
    eta_end: datetime


app = FastAPI(title="Northbound Dispatch ETA service", version=__version__)


def _hub(code: str):
    try:
        return get_hub(code)
    except UnknownHub:
        raise HTTPException(status_code=404, detail=f"unknown hub: {code}") from None


def _lane(origin: str, destination: str):
    try:
        return lane(_hub(origin), _hub(destination))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"service": "northbound-dispatch-api", "version": __version__}


@app.get("/hubs", response_model=list[HubOut])
def hubs() -> list[HubOut]:
    return [HubOut(code=h.code, name=h.name, country=h.country) for h in HUBS.values()]


@app.get("/lanes/{origin}/{destination}", response_model=LaneOut)
def get_lane(origin: str, destination: str) -> LaneOut:
    ln = _lane(origin, destination)
    return LaneOut(
        origin=ln.origin.code,
        destination=ln.destination.code,
        distance_km=ln.distance_km,
        road_km=ln.road_km,
        cross_border=ln.cross_border,
        transit_days={s: transit_days(ln, s) for s in Service},
    )


@app.post("/eta", response_model=EtaOut)
def post_eta(req: EtaRequest) -> EtaOut:
    ln = _lane(req.origin, req.destination)
    w = estimate(ln.origin, ln.destination, req.service, req.pickup)
    return EtaOut(
        origin=ln.origin.code,
        destination=ln.destination.code,
        service=w.service,
        transit_days=w.transit_days,
        dispatch_day=w.dispatch_day.date().isoformat(),
        eta_start=w.eta_start,
        eta_end=w.eta_end,
    )
