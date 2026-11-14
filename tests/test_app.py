from fastapi.testclient import TestClient

from northbound_api import __version__
from northbound_api.app import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version():
    assert client.get("/version").json() == {"service": "northbound-dispatch-api", "version": __version__}


def test_hubs_lists_the_network():
    hubs = client.get("/hubs").json()
    codes = {h["code"] for h in hubs}
    assert {"HEL", "TLL", "OUL", "STO"} <= codes
    assert all(set(h) == {"code", "name", "country"} for h in hubs)


def test_lane():
    r = client.get("/lanes/hel/tll")
    assert r.status_code == 200
    body = r.json()
    assert body["origin"] == "HEL" and body["destination"] == "TLL"
    assert body["crossBorder"] is True
    assert 78 < body["distanceKm"] < 86
    assert body["roadKm"] > body["distanceKm"]
    assert set(body["transitDays"]) == {"express", "standard", "economy"}


def test_lane_unknown_hub_is_404():
    r = client.get("/lanes/HEL/XXX")
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown hub: XXX"


def test_lane_to_itself_is_422():
    assert client.get("/lanes/HEL/HEL").status_code == 422


def test_eta_uses_the_web_service_field_names():
    r = client.post(
        "/eta",
        json={"origin": "HEL", "destination": "TMP", "service": "express", "pickup": "2026-11-12T09:00:00Z"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["etaStart"] == "2026-11-13T08:00:00Z"
    assert body["etaEnd"] == "2026-11-13T18:00:00Z"
    assert body["dispatchDay"] == "2026-11-12"
    assert body["transitDays"] == 1


def test_eta_defaults_to_standard_service():
    r = client.post("/eta", json={"origin": "HEL", "destination": "OUL", "pickup": "2026-11-09T09:00:00+02:00"})
    assert r.status_code == 200
    assert r.json()["service"] == "standard"


def test_eta_rejects_a_pickup_without_time_zone():
    r = client.post("/eta", json={"origin": "HEL", "destination": "OUL", "pickup": "2026-11-09T09:00:00"})
    assert r.status_code == 422


def test_eta_rejects_an_unknown_service():
    r = client.post(
        "/eta",
        json={"origin": "HEL", "destination": "OUL", "service": "teleport", "pickup": "2026-11-09T09:00:00Z"},
    )
    assert r.status_code == 422
