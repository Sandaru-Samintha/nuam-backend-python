from fastapi import WebSocket
from typing import List

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        print("New device added tot the list")
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # print("Broadcasting message to frontend clients:", message)

        disconnected_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print("WebSocket error:", e)
                disconnected_connections.append(connection)
         # Remove broken connections
        for connection in disconnected_connections:
            self.disconnect(connection)


manager = WebSocketManager()
