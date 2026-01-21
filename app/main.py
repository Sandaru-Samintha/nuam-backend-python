from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.core.database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"message": "FastAPI WebSocket Server Running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    try:
        while True:
            data = await websocket.receive_text()
            print("Received:", data)

            # send back to client
            await websocket.send_text(f"Server received: {data}")

    except WebSocketDisconnect:
        print("Client disconnected")

