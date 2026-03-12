from fastapi import APIRouter
from app.services.network_transformer import (
    build_dashboard_response
)

router = APIRouter(prefix="/api/network", tags=["Network"])

# Store latest collector state
latest_topology = {}
latest_metrics = {}


# Collector sends data here
@router.post("/collector")
async def receive_collector_data(data: dict):

    global latest_topology
    global latest_metrics

    data_type = data.get("type")
    subtype = data.get("subtype")
    payload = data.get("payload", {})

    if data_type == "TOPOLOGY":
        latest_topology = payload.get("topology", {})

    if data_type == "METRIC":
        latest_metrics = payload.get("metrics", {})

    return {"status": "received"}


# Frontend dashboard endpoint
@router.get("/dashboard")
async def get_dashboard():

    return build_dashboard_response(
        latest_metrics,
        latest_topology
    )