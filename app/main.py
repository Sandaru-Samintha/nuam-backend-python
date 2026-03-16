from fastapi import FastAPI, WebSocket, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, get_db
from app.models.device_event import Base, DeviceEvent

from app.services.websocket_manager import manager
from app.services.event_processor import EventProcessor
from app.services.network_transformer import (
    build_network_stats,
    build_ip_devices,
    build_ip_alerts,
    build_dashboard_response
)

from app.api.frontend_ws import frontend_ws
from app.api import analytics, topology_router, reports, ip_address_management
from app.api.topology_router import build_topology_response


app = FastAPI(title="Network Device Monitoring")

# Global state
latest_topology = {}
latest_metrics = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(analytics.router)
app.include_router(topology_router.router)
app.include_router(reports.router)
app.include_router(ip_address_management.router)


# REST API
@app.get("/device-events")
def get_device_events(db: Session = Depends(get_db)):
    return db.query(DeviceEvent).all()



# WebSocket for Collector
@app.websocket("/ws/device")
async def device_ws(websocket: WebSocket):

    global latest_topology
    global latest_metrics

    await manager.connect(websocket)

    db = SessionLocal()
    processor = EventProcessor(db)

    try:
        while True:

            data = await websocket.receive_json()

            # print("Data Received:", data)

            # Save event to DB
            processor.process_event(data)

            data_type = data.get("type")
            payload = data.get("payload", {})

            # Update topology
            if data_type == "TOPOLOGY" and "topology" in payload:
                latest_topology = payload["topology"]

            # Update metrics
            if data_type == "METRIC" and "metrics" in payload:
                latest_metrics = payload["metrics"]
                
            # topology_data = None
                
            if data["type"] == "TOPOLOGY" and "topology" in data["payload"]:
                topology_data = build_topology_response(data["payload"]["topology"])
                

            # Build responses
            ip_address_management = build_dashboard_response(latest_metrics,latest_topology)
            

            ws_message = {
                "event": data,
                "ip_address_management": ip_address_management,
                "dashboard_stats": processor.get_dashboard_stats(),
                "topology": topology_data
            }

            # Broadcast to all clients
            await manager.broadcast(ws_message)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    finally:
        db.close()


# WebSocket for Frontend
@app.websocket("/ws/frontend")
async def ws_frontend(websocket: WebSocket):
    await frontend_ws(websocket)