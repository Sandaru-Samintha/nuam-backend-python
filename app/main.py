from fastapi import FastAPI, WebSocket, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import SessionLocal
from app.api.frontend_ws import frontend_ws
from app.core.database import engine, get_db
from app.models.device_event import Base
from app.models.device_event import DeviceEvent
from sqlalchemy.orm import Session
from app.services.websocket_manager import manager
from app.services.event_processor import EventProcessor
from datetime import datetime
from app.api import analytics
from app.api import topology_router
from app.api import network_activity
from app.api import reports
from app.api.topology_router import build_topology_response

app = FastAPI(title="Network Device Monitoring")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(analytics.router)

app.include_router(topology_router.router)

app.include_router(network_activity.router)
app.include_router(reports.router)

@app.get("/device-events")
def get_device_events(db: Session = Depends(get_db)):
    device_events = db.query(DeviceEvent).all()
    return device_events

@app.websocket("/ws/device")
async def device_ws(websocket: WebSocket):
    await manager.connect(websocket)

    db = SessionLocal()
    processor = EventProcessor(db)

    try:
        while True:
            data = await websocket.receive_json()
            
            print("Data Received : " , data)

            # Save event to DB
            processor.process_event(data)

            # Calculate dashboard stats
            stats = processor.get_dashboard_stats()
            
            if data["type"] == "TOPOLOGY" and "topology" in data["payload"]:
                topology_data = build_topology_response(data["payload"]["topology"])

                enriched_data = {
                    "event": data,
                    "dashboard_stats": processor.get_dashboard_stats(),
                    "topology": topology_data
                }
                

                await manager.broadcast(enriched_data)           

            # Attach stats to outgoing message
            enriched_data = {
                "event": data,
                "dashboard_stats": stats
            }

            # Broadcast enriched message
            await manager.broadcast(enriched_data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        db.close()

@app.websocket("/ws/frontend")
async def ws_frontend(websocket: WebSocket):
    await frontend_ws(websocket)
