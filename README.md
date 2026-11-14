# Northbound Dispatch — api

ETA service for the fictional logistics company Northbound Dispatch: lanes between
hubs and delivery windows for shipments. The web service
(`Helios-One-Oy/parallax-demo-web`) stores a shipment's `etaStart` and `etaEnd`;
this service works them out.

Part of the Parallax fleet (`Helios-One-Oy/parallax-demo-api`): its CI runs twice on
CRACI runners (a bare twin and a decoy twin) so Parallax can diff their network
traces.

## Stack

Python 3.12, FastAPI, pydantic, uvicorn, pytest.

## Routes

- `GET /healthz` — liveness
- `GET /version` — service name and version
- `GET /hubs` — the hubs in the network
- `GET /lanes/{origin}/{destination}` — distance, border crossing and working days on the road per service level
- `POST /eta` — delivery window for a pickup time: `{"origin": "HEL", "destination": "OUL", "service": "standard", "pickup": "2026-11-09T09:00:00Z"}`

## The model

Great-circle distance between hubs times a road detour factor of 1.25, a daily
line-haul range per service level (express 900 km, standard 550 km, economy 350 km),
one extra day when a lane crosses a border, no movement on Saturdays and Sundays,
and a 14:00 UTC cut-off. Public holidays are not modelled.

## Dependencies

`pyproject.toml` names the direct dependencies. `requirements.lock` pins every
package with its hashes; CI installs with `pip install --require-hashes`, so a
package whose bytes changed is refused. Update the lock with:

```
uv pip compile pyproject.toml --extra dev --generate-hashes --python-version 3.12 -o requirements.lock
```

## Develop

```
python -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements.lock
python -m pytest
python -m northbound_api
```
