from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import json

from app.models.device import Device
from app.models.device_event import DeviceEvent
from app.models.network_metrics import NetworkMetric

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary_by_date(self, target_date: date):
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # Devices that had any event on this date
        active_ids_today = self.db.query(DeviceEvent.device_id).filter(
            and_(
                DeviceEvent.timestamp >= start_datetime,
                DeviceEvent.timestamp <= end_datetime
            )
        ).distinct().all()
        active_ids_today = [d[0] for d in active_ids_today]

        # Connected devices (Unique devices seen in events)
        total_connected = len(active_ids_today)

        # Peak active devices from metrics
        peak_active = self.db.query(func.max(NetworkMetric.active_devices)).filter(
            and_(
                NetworkMetric.measure_time >= start_datetime,
                NetworkMetric.measure_time <= end_datetime
            )
        ).scalar() or 0

        # Inactive devices: Devices that were seen before this date but NOT on this date
        total_devices_ever = self.db.query(Device).filter(
            Device.first_seen <= end_datetime
        ).count()
        inactive_count = total_devices_ever - total_connected

        # Traffic
        traffic = self.db.query(
            func.sum(NetworkMetric.data_sent).label("sent"),
            func.sum(NetworkMetric.data_received).label("received"),
            func.sum(NetworkMetric.total_packets).label("packets")
        ).filter(
            and_(
                NetworkMetric.measure_time >= start_datetime,
                NetworkMetric.measure_time <= end_datetime
            )
        ).first()

        # Handle None results from sum()
        sent_mb = round((traffic.sent or 0) / (1024 * 1024), 2) if traffic else 0
        received_mb = round((traffic.received or 0) / (1024 * 1024), 2) if traffic else 0
        total_packets = int(traffic.packets or 0) if traffic else 0

        return {
            "date": target_date.isoformat(),
            "summary": {
                "connected_devices_count": total_connected,
                "peak_active_concurrently": peak_active,
                "inactive_devices_count": max(0, inactive_count),
                "total_traffic": {
                    "sent_mb": sent_mb,
                    "received_mb": received_mb,
                    "total_packets": total_packets
                }
            },
            "device_ids": active_ids_today
        }

    def get_device_detail_report(self, device_id: str, target_date: date):
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        device = self.db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return None

        # Connection frequency (How many times did they join?)
        connection_events = self.db.query(DeviceEvent).filter(
            and_(
                DeviceEvent.device_id == device_id,
                DeviceEvent.event_type == "DEVICE_JOINED",
                DeviceEvent.timestamp >= start_datetime,
                DeviceEvent.timestamp <= end_datetime
            )
        ).count()

        # Activities (What did they access?)
        # Based on models, access_logs and access_services are in Device model,
        # but for history we might need to check events.
        # Assuming events raw_json might contain more info.
        events = self.db.query(DeviceEvent).filter(
            and_(
                DeviceEvent.device_id == device_id,
                DeviceEvent.timestamp >= start_datetime,
                DeviceEvent.timestamp <= end_datetime
            )
        ).order_by(DeviceEvent.timestamp.asc()).all()

        activities = []
        for event in events:
            try:
                data = json.loads(event.raw_json) if event.raw_json else {}
            except:
                data = {}
            
            activities.append({
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "details": data
            })

        # Calculate connection duration
        # Simplified: Time between JOINED and LEFT events
        duration_seconds = 0
        last_join_time = None
        
        for event in events:
            if event.event_type == "DEVICE_JOINED":
                last_join_time = event.timestamp
            elif event.event_type == "DEVICE_LEFT" and last_join_time:
                duration_seconds += (event.timestamp - last_join_time).total_seconds()
                last_join_time = None
        
        # If still connected at the end of the day or currently
        if last_join_time:
            # If the date is today, use current time, else end of that day
            if target_date == datetime.utcnow().date():
                end_calc = datetime.utcnow()
            else:
                end_calc = end_datetime
            duration_seconds += (end_calc - last_join_time).total_seconds()

        return {
            "device_info": {
                "device_id": device.device_id,
                "hostname": device.hostname,
                "ip_address": device.ip_address,
                "vendor": device.vendor,
                "device_type": device.device_type,
                "os": device.os
            },
            "report_date": target_date.isoformat(),
            "metrics": {
                "connection_count": connection_events,
                "total_duration_minutes": round(duration_seconds / 60, 2),
                "data_sent_bytes": device.data_sent if target_date == datetime.utcnow().date() else 0, # Note: this model stores totals, historical per-day would need another table or diffs
                "data_received_bytes": device.data_received if target_date == datetime.utcnow().date() else 0
            },
            "activities": activities
        }
