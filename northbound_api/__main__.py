"""`python -m northbound_api` starts the service on port 8080."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("northbound_api.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
