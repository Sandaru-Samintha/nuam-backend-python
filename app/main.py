from fastapi import FastAPI, WebSocket, Depends
from app.api.device_ws import device_websocket
from app.api.frontend_ws import frontend_ws
from app.core.database import engine, get_db
from app.models.device_event import Base
from app.models.device_event import DeviceEvent
from sqlalchemy.orm import Session

app = FastAPI(title="Network Device Monitoring")

Base.metadata.create_all(bind=engine)

@app.get("/device-events")
def get_device_events(db: Session = Depends(get_db)):
    device_events = db.query(DeviceEvent).all()
    return device_events

@app.websocket("/ws/device")
async def ws_device(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            print("[DEVICE EVENT]", data)
    except:
        print("[DEVICE DISCONNECTED]")



@app.websocket("/ws/frontend")
async def ws_frontend(websocket: WebSocket):
    await frontend_ws(websocket)
