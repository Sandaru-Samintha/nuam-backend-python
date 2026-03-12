from typing import Dict, List
import uuid


# Map device types
def map_device_type(db_type: str | None) -> str:
    mapping = {
        "LAPTOP": "PC",
        "MOBILE": "Mobile",
        "PRINTER": "IoT",
        "IOT": "IoT",
        "NETWORK": "Router"
    }
    return mapping.get(db_type, "Unknown")



# Network Stats Builder
def build_network_stats(metrics_data: Dict, topology: Dict):

    devices = topology.get("devices", [])

    total_ips = 254
    in_use = len(devices)
    available = total_ips - in_use

    conflicts = sum(1 for d in devices if d.get("status") == "conflict")
    unauthorized = sum(1 for d in devices if d.get("status") == "unauthorized")

    return {
        "totalIPs": total_ips,
        "inUse": in_use,
        "available": available,
        "conflicts": conflicts,
        "unauthorized": unauthorized,
        "poolRange": "10.0.0.1 - 10.0.0.254"
    }


# Build IP Devices
def build_ip_devices(topology: Dict):

    devices = topology.get("devices", [])

    device_list: List[Dict] = []

    for d in devices:

        if d.get("status") == "conflict":
            risk = "Conflict"
        elif not d.get("online"):
            risk = "Unauthorized"
        else:
            risk = "Normal"

        device_list.append({
            "id": d.get("mac"),
            "ipAddress": d.get("ip_address"),
            "macAddress": d.get("mac"),

            "deviceName": d.get("hostname") or "Unknown",

            "hostType": map_device_type(d.get("device_type")),

            "assignedBy": "DHCP",

            "leaseStatus": "Active" if d.get("online") else "Expired",

            "firstSeen": d.get("first_seen"),
            "lastSeen": d.get("last_seen"),

            "riskStatus": "",

            "macVendor": d.get("vendor"),

            "connectionDuration": "",

            "userAgent": d.get("os")
        })

    return device_list


# Build Alerts
def build_ip_alerts(topology: Dict):

    devices = topology.get("devices", [])

    alerts = []

    for d in devices:

        if not d.get("online"):

            alerts.append({
                "id": str(uuid.uuid4()),

                "timestamp": d.get("last_seen"),

                "type": "Unauthorized",

                "severity": "Medium",

                "description": f"Device {d.get('ip_address')} disconnected",

                "affectedIPs": [d.get("ip_address")],

                "status": "Active"
            })

    return alerts



# Build Dashboard Response
def build_dashboard_response(metrics_data: Dict, topology: Dict):

    return {
        "networkStats": build_network_stats(metrics_data, topology),
        "devices": build_ip_devices(topology),
        "alerts": build_ip_alerts(topology)
    }