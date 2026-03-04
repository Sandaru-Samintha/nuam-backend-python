from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio

from app.core.database import get_db
from app.models.device import Device

router = APIRouter(prefix="/api/topology", tags=["Topology"])




# Helper Functions
def map_device_type(db_type: str | None) -> str:
    mapping = {
        "LAPTOP": "laptop",
        "MOBILE": "mobile",
        "PRINTER": "printer",
        "IOT": "iot",
        "NETWORK": "network"
    }
    return mapping.get(db_type, "network")



def build_topology_response(topology):

    devices = topology.get("devices", [])

    total_packets = sum(d.get("packet_count", 0) for d in devices)

    device_list = []

    for d in devices:
        packet_count = d.get("packet_count", 0)

        activity_percent = (
            (packet_count / total_packets) * 100
            if total_packets > 0 else 0
        )

        if activity_percent > 50:
            activity_level = "high"
        elif activity_percent > 20:
            activity_level = "medium"
        else:
            activity_level = "low"

        device_list.append({
            "id": d.get("mac"),
            "name": d.get("hostname") or d.get("mac"),
            "ip": d.get("ip_address"),
            "device_id": d.get("mac"),
            "vendor": d.get("vendor"),
            "type": d.get("device_type"),
            "status": d.get("status"),
            "online": d.get("online"),
            "firstSeen": d.get("first_seen"),
            "lastSeen": d.get("last_seen"),
            "activityLevel": activity_level,
            "activityPercent": round(activity_percent, 2),
            "data_sent": d.get("data_sent", 0),
            "data_received": d.get("data_received", 0),
            "packet_count": packet_count
        })
        

    return {
        "switch": {
            "id": "core-switch-1",
            "name": "Core Switch",
            "x": 400,
            "y": 300
        },
        "devices": device_list
    }