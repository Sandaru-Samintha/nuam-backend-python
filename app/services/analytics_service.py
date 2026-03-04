from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func

from app.models.device import Device
from app.models.device_event import DeviceEvent
from app.models.network_metrics import NetworkMetric

class AnalyticsService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_stats(self):
        today = datetime.utcnow().date()

        new_devices_today = self.db.query(Device).filter(func.date(Device.first_seen) == today).count()
        inactive_devices = self.db.query(Device).filter(Device.status == "INACTIVE").count()
        total_devices = self.db.query(Device).count()
        active_devices = self.db.query(Device).filter(Device.status == "ACTIVE").count()

        return {
            "new_devices_today": new_devices_today,
            "inactive_devices": inactive_devices,
            "active_devices": active_devices,
            "total_devices": total_devices
        }
    
    def get_traffic_summary(self):

        last_hour = datetime.utcnow() - timedelta(hours=1)

        result = self.db.query(
            func.sum(NetworkMetric.total_packets),
            func.sum(NetworkMetric.tcp_packets),
            func.sum(NetworkMetric.udp_packets),
            func.sum(NetworkMetric.icmp_packets),
            func.sum(NetworkMetric.arp_requests),
            func.sum(NetworkMetric.data_sent),
            func.sum(NetworkMetric.data_received),
        ).filter(
            NetworkMetric.measure_time >= last_hour
        ).first()

        if result and result[0]:
            return {
                "total_packets": result[0],
                "tcp_packets": result[1],
                "udp_packets": result[2],
                "icmp_packets": result[3],
                "arp_requests": result[4],
                "data_sent_mb": round(result[5] / (1024 * 1024), 2),
                "data_received_mb": round(result[6] / (1024 * 1024), 2)
            }

        return {
            "total_packets": 0,
            "tcp_packets": 0,
            "udp_packets": 0,
            "icmp_packets": 0,
            "arp_requests": 0,
            "data_sent_mb": 0,
            "data_received_mb": 0
        }
    
    def get_device_connections_today(self):
        today = datetime.utcnow().date()
        
        connections = self.db.query(DeviceEvent).filter(
            DeviceEvent.event_type == "DEVICE_JOINED",
            func.date(DeviceEvent.timestamp) == today
        ).count()
        
        return {
            "total_connections_today": connections
        }
    
    def get_protocol_distribution(self):
        last_5_min = datetime.utcnow() - timedelta(minutes=5)

        result = self.db.query(
            func.coalesce(func.sum(NetworkMetric.tcp_packets), 0),
            func.coalesce(func.sum(NetworkMetric.udp_packets), 0),
            func.coalesce(func.sum(NetworkMetric.icmp_packets), 0),
            func.coalesce(func.sum(NetworkMetric.arp_requests), 0),
            func.coalesce(func.sum(NetworkMetric.total_packets), 0)
        ).filter(
            NetworkMetric.measure_time >= last_5_min
        ).first()

        tcp, udp, icmp, arp, total = result

        if total > 0:
            return {
                "tcp_percentage": round((tcp / total) * 100, 2),
                "udp_percentage": round((udp / total) * 100, 2),
                "icmp_percentage": round((icmp / total) * 100, 2),
                "arp_percentage": round((arp / total) * 100, 2)
            }

        return {
            "tcp_percentage": 0,
            "udp_percentage": 0,
            "icmp_percentage": 0,
            "arp_percentage": 0
        }
    
    def get_all_devices(self):
        devices = self.db.query(Device).all()
        device_list = []
        
        for device in devices:
            last_hour = datetime.utcnow() - timedelta(hours=1)
            device_events = self.db.query(DeviceEvent).filter(
                DeviceEvent.device_id == device.device_id,
                DeviceEvent.timestamp >= last_hour
            ).count()
            
            device_list.append({
                "device_id": device.device_id,
                "ip": device.ip_address,
                "vendor": device.vendor,
                "status": device.status,
                "first_seen": device.first_seen.isoformat() if device.first_seen else None,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "activity_count_last_hour": device_events,
                "hostname": device.hostname or "Unknown"
            })
        
        return device_list
    
    def get_network_health(self):
        last_10_min = datetime.utcnow() - timedelta(minutes=10)
        
        metrics = self.db.query(NetworkMetric).filter(
            NetworkMetric.measure_time >= last_10_min
        ).order_by(NetworkMetric.measure_time.desc()).first()
        
        if not metrics:
            return {
                "health_score": 100, 
                "issues": [], 
                "status": "HEALTHY"
            }
        
        issues = []
        score = 100
        
        if metrics.arp_requests > (metrics.total_packets * 0.3):
            score -= 20
            issues.append("ARP traffic unusually high")
        
        if metrics.total_packets > 10000:
            score -= 15
            issues.append("High network traffic")
        
        if metrics.udp_packets > metrics.tcp_packets * 2:
            score -= 10
            issues.append("Unusual UDP/TCP ratio")
        
        if score > 80:
            status = "HEALTHY"
        elif score > 50:
            status = "WARNING"
        else:
            status = "CRITICAL"
        
        return {
            "health_score": max(0, score),
            "issues": issues,
            "status": status
        }
    
    def get_complete_analytics(self):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "dashboard_stats": self.get_dashboard_stats(),
            "traffic_summary": self.get_traffic_summary(),
            "device_connections": self.get_device_connections_today(),
            "protocol_distribution": self.get_protocol_distribution(),
            "devices": self.get_all_devices(),
            "network_health": self.get_network_health()
        }