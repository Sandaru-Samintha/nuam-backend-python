import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.device import Device
from app.models.device_event import DeviceEvent
from app.models.network_metrics import NetworkMetric


class EventProcessor:

    def __init__(self, db: Session):
        self.db = db

    def process_event(self, message: dict):
        try:
            subtype = message.get("subtype")
            payload = message.get("payload")

            if subtype == "DEVICE_JOINED":
                self.handle_device_joined(payload)
            elif subtype == "DEVICE_IDLE":
                self.handle_device_idle(payload)
            elif subtype == "PERIODIC_METRIC_STATE":
                self.handle_metric(payload)
            elif subtype == "PERIODIC_TOPOLOGY_STATE":
                self.handle_topology_snapshot(payload['topology']['devices'])

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def handle_device_joined(self, payload):
        device_data = payload["device"]
        mac = device_data["device_id"]
        timestamp = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

        device = self.db.query(Device).filter_by(device_id=mac).first()
        if not device:
            device = Device(
                device_id=mac,
                hostname=device_data.get("hostname"),
                ip_address=device_data.get("ip_address"),
                device_type=device_data.get("device_type"),
                os=device_data.get("os"),
                vendor=device_data.get("vendor"),
                first_seen=timestamp,
                last_seen=timestamp,
                status="active",
                online=True,
                data_sent=0,
                data_received=0,
                packet_count=0,
            )
            self.db.add(device)
        else:
            device.last_seen = timestamp
            device.status = "active"
            device.online = True

        event = DeviceEvent(
            device_id=mac,
            event_type="DEVICE_JOINED",
            timestamp=timestamp,
            raw_json=json.dumps(payload)
        )
        self.db.add(event)

    def handle_device_idle(self, payload):
        device_data = payload["device"]
        mac = device_data["device_id"]
        timestamp = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

        device = self.db.query(Device).filter_by(device_id=mac).first()
        if device:
            device.status = "idle"
            device.online = True
            device.last_seen = timestamp

        event = DeviceEvent(
            device_id=mac,
            event_type="DEVICE_IDLE",
            timestamp=timestamp,
            raw_json=json.dumps(payload)
        )
        self.db.add(event)

    def handle_metric(self, payload):
        metrics = payload["metrics"]
        metric_row = NetworkMetric(
            measure_time=datetime.fromisoformat(metrics["measure_time"].replace("Z", "+00:00")),
            total_devices=metrics.get("total_devices", 0),
            active_devices=metrics.get("active_devices", 0),
            data_sent=metrics.get("data_sent", 0),
            data_received=metrics.get("data_received", 0),
            arp_requests=metrics.get("arp_requests", 0),
            tcp_packets=metrics.get("tcp_packets", 0),
            udp_packets=metrics.get("udp_packets", 0),
            icmp_packets=metrics.get("icmp_packets", 0),
            total_packets=metrics.get("total_packets", 0)
        )
        self.db.add(metric_row)

    def handle_topology_snapshot(self, devices_payload):
        for device_data in devices_payload:
            mac = device_data["mac"]

            device = self.db.query(Device).filter_by(device_id=mac).first()

            first_seen_dt = datetime.fromisoformat(device_data.get("first_seen").replace("Z", "+00:00")) \
                if device_data.get("first_seen") else datetime.now(timezone.utc)
            last_seen_dt = datetime.fromisoformat(device_data.get("last_seen").replace("Z", "+00:00")) \
                if device_data.get("last_seen") else datetime.now(timezone.utc)

            status = device_data.get("status", "active")

            if not device:
                device = Device(
                    device_id=mac,
                    hostname=device_data.get("hostname"),
                    ip_address=device_data.get("ip_address"),
                    device_type=device_data.get("device_type"),
                    os=device_data.get("os"),
                    vendor=device_data.get("vendor"),
                    first_seen=first_seen_dt,
                    last_seen=last_seen_dt,
                    status=status,
                    online=(status != "left"),
                    data_sent=device_data.get("data_sent", 0),
                    data_received=device_data.get("data_received", 0),
                    packet_count=device_data.get("packet_count", 0),
                )
                self.db.add(device)
            else:
                device.hostname = device_data.get("hostname")
                device.ip_address = device_data.get("ip_address")
                device.device_type = device_data.get("device_type")
                device.os = device_data.get("os")
                device.vendor = device_data.get("vendor")
                device.last_seen = last_seen_dt
                device.status = status
                device.online = (status != "left")
                device.data_sent = device_data.get("data_sent", 0)
                device.data_received = device_data.get("data_received", 0)
                device.packet_count = device_data.get("packet_count", 0)
                if not device.first_seen:
                    device.first_seen = first_seen_dt

    # Function to print all table data for debugging
    def print_all_data(self):
        print("\n=== Devices Table ===")
        for d in self.db.query(Device).all():
            print(vars(d))
        
        print("\n=== Network Metrics Table ===")
        for n in self.db.query(NetworkMetric).all():
            print(vars(n))
        
        print("\n=== Device Events Table ===")
        for e in self.db.query(DeviceEvent).all():
            print(vars(e))

    def get_dashboard_stats(self):
        today = datetime.now(timezone.utc).date()

        new_devices_today = self.db.query(Device).filter(
            func.date(Device.first_seen) == today
        ).count()

        active_devices = self.db.query(Device).filter(Device.status == "active").count()
        idle_devices = self.db.query(Device).filter(Device.status == "idle").count()
        left_devices = self.db.query(Device).filter(Device.status == "left").count()
        total_devices = self.db.query(Device).count()

        devices = self.db.query(Device).all()
        device_list = [
            {
                "id": d.device_id,
                "name": d.hostname,
                "ip": d.ip_address,
                "mac": d.device_id,
                "vendor": d.vendor,
                "type": d.device_type,
                "status": d.status,
                "lastSeen": d.last_seen.isoformat() if d.last_seen else None
            }
            for d in devices
        ]

        return {
            "new_devices_today": new_devices_today,
            "active_devices": active_devices,
            "idle_devices": idle_devices,
            "left_devices": left_devices,
            "total_devices": total_devices,
            "devices": device_list
        }