from fastapi import WebSocketDisconnect
from app.services.network_state import network_state
from app.services.websocket_manager import manager
import json

async def frontend_ws(websocket):
    await manager.connect(websocket)

    try:
        while True:
            data_str = await websocket.receive_text()

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = {}

            # Handle subnet update
            device_ip = data.get("newDeviceIP")
            subnet_mask = data.get("subnetMask")
            

            if subnet_mask:
                try:
                    if device_ip and subnet_mask:
                        network_state.validate_subnet_mask(subnet_mask)
                        network_state.update_subnet(device_ip, subnet_mask)

                except ValueError:
                    await websocket.send_json({
                        "error": "Invalid subnet mask"
                    })
                    continue

            from app.services.network_transformer import build_dashboard_response
            from app.core.database import SessionLocal

            db = SessionLocal()

            try:
                dashboard = build_dashboard_response({}, {})

                dashboard["networkStats"]["totalIPs"] = network_state.total_ips
                dashboard["networkStats"]["poolRange"] = network_state.pool_range

                await manager.broadcast({
                    "networkStats": {
                        "totalIPs": network_state.total_ips,
                        "poolRange": network_state.pool_range
                    }
                })

            finally:
                db.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        return