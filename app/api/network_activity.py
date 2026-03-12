from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import deque
import statistics

from app.core.database import get_db
from app.models.device import Device

router = APIRouter(prefix="/api/network", tags=["Network Activity"])

class NetworkActivityManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.metric_history: deque = deque(maxlen=60)  # Store last 60 metrics
        self.packet_rate_history: deque = deque(maxlen=60)  # Packets per second history
        self.arp_history: deque = deque(maxlen=30)  # ARP activity history
        self.last_metrics = None
        self.last_update_time = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast_activity_data(self, data: dict):
        """Broadcast network activity data to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                pass

    def calculate_packet_rate(self, current_metrics, time_diff_seconds):
        """Calculate packets per second"""
        if self.last_metrics and time_diff_seconds > 0:
            packets_diff = (
                current_metrics.get('total_packets', 0) - 
                self.last_metrics.get('total_packets', 0)
            )
            return round(packets_diff / time_diff_seconds, 2)
        return 0

    def calculate_network_load(self, current_metrics, time_diff_seconds):
        """Calculate network load in bytes per second"""
        if self.last_metrics and time_diff_seconds > 0:
            data_diff = (
                current_metrics.get('data_sent', 0) + 
                current_metrics.get('data_received', 0) -
                self.last_metrics.get('data_sent', 0) - 
                self.last_metrics.get('data_received', 0)
            )
            return round(data_diff / time_diff_seconds, 2)
        return 0

    def process_metrics(self, raw_data: dict) -> dict:
        """Process raw metric data and calculate derived metrics"""
        try:
            metrics = raw_data.get('payload', {}).get('metrics', {})
            current_time = datetime.now()
            time_diff = 0
            
            if self.last_update_time:
                time_diff = (current_time - self.last_update_time).total_seconds()
            
            # Calculate packets per second
            packets_per_second = self.calculate_packet_rate(metrics, time_diff)
            
            # Calculate network load
            network_load = self.calculate_network_load(metrics, time_diff)
            
            # Calculate ARP request rate
            arp_requests = metrics.get('arp_requests', 0)
            arp_replies = metrics.get('arp_replies', 0)
            arp_total = arp_requests + arp_replies
            arp_rate = round(arp_total / time_diff, 2) if time_diff > 0 else 0
            
            # Calculate traffic distribution
            broadcast_packets = metrics.get('total_broadcast_packets', 0)
            unicast_packets = metrics.get('total_unicast_packets', 0)
            total_packets = metrics.get('total_packets', 0)
            
            broadcast_percentage = round((broadcast_packets / total_packets * 100), 2) if total_packets > 0 else 0
            unicast_percentage = round((unicast_packets / total_packets * 100), 2) if total_packets > 0 else 0
            
            # Store in history
            packet_rate_data = {
                'timestamp': current_time.isoformat(),
                'value': packets_per_second,
                'broadcast': broadcast_packets,
                'unicast': unicast_packets
            }
            self.packet_rate_history.append(packet_rate_data)
            
            arp_data = {
                'timestamp': current_time.isoformat(),
                'requests': arp_requests,
                'replies': arp_replies
            }
            self.arp_history.append(arp_data)
            
            # Update last values
            self.last_metrics = metrics
            self.last_update_time = current_time
            
            # Generate network insights
            insights = self.generate_insights(metrics, packets_per_second, arp_rate)
            
            return {
                'timestamp': current_time.isoformat(),
                'packets_per_second': packets_per_second,
                'active_devices': metrics.get('active_devices', 0),
                'total_devices': metrics.get('total_devices', 0),
                'arp_requests_rate': arp_rate,
                'arp_requests_total': arp_requests,
                'arp_replies_total': arp_replies,
                'broadcast_traffic': broadcast_packets,
                'unicast_traffic': unicast_packets,
                'broadcast_percentage': broadcast_percentage,
                'unicast_percentage': unicast_percentage,
                'network_load': network_load,
                'data_sent': metrics.get('data_sent', 0),
                'data_received': metrics.get('data_received', 0),
                'total_packets': total_packets,
                'tcp_packets': metrics.get('tcp_packets', 0),
                'udp_packets': metrics.get('udp_packets', 0),
                'dns_queries': metrics.get('dns_queries', 0),
                'dhcp_packets': metrics.get('dhcp_packets', 0),
                'packet_rate_history': list(self.packet_rate_history),
                'arp_history': list(self.arp_history),
                'insights': insights
            }
            
        except Exception as e:
            print(f"Error processing metrics: {e}")
            return {}

    def generate_insights(self, metrics: dict, packet_rate: float, arp_rate: float) -> List[dict]:
        """Generate automated insights from network activity"""
        insights = []
        
        # Check for high packet rate
        if packet_rate > 100:
            insights.append({
                'type': 'warning',
                'title': 'High Packet Rate Detected',
                'description': f'Network is experiencing high packet rate of {packet_rate} packets/sec',
                'timestamp': datetime.now().isoformat()
            })
        elif packet_rate > 50:
            insights.append({
                'type': 'info',
                'title': 'Moderate Network Activity',
                'description': f'Current packet rate is {packet_rate} packets/sec',
                'timestamp': datetime.now().isoformat()
            })
            
        # Check ARP activity
        if arp_rate > 10:
            insights.append({
                'type': 'warning',
                'title': 'High ARP Activity',
                'description': f'Unusual ARP activity detected: {arp_rate} ARP packets/sec',
                'timestamp': datetime.now().isoformat()
            })
            
        # Check traffic distribution
        broadcast_pct = (metrics.get('total_broadcast_packets', 0) / 
                        max(metrics.get('total_packets', 1), 1)) * 100
        if broadcast_pct > 30:
            insights.append({
                'type': 'info',
                'title': 'High Broadcast Traffic',
                'description': f'Broadcast traffic is {broadcast_pct:.1f}% of total traffic',
                'timestamp': datetime.now().isoformat()
            })
            
        # Check protocol distribution
        tcp_packets = metrics.get('tcp_packets', 0)
        udp_packets = metrics.get('udp_packets', 0)
        if tcp_packets > udp_packets * 2:
            insights.append({
                'type': 'info',
                'title': 'TCP Dominant Traffic',
                'description': 'Most traffic is TCP-based, indicating file transfers or web traffic',
                'timestamp': datetime.now().isoformat()
            })
        elif udp_packets > tcp_packets * 2:
            insights.append({
                'type': 'info',
                'title': 'UDP Dominant Traffic',
                'description': 'High UDP traffic detected, possibly streaming or VoIP',
                'timestamp': datetime.now().isoformat()
            })
            
        return insights

class DeviceActivityTracker:
    def __init__(self):
        self.devices = {}  # Store device information
        self.device_history = deque(maxlen=100)  # Store recent device activities
        
    def update_devices(self, topology_data: dict):
        """Update device information from topology snapshot"""
        try:
            devices = topology_data.get('payload', {}).get('topology', {}).get('devices', [])
            current_time = datetime.now()
            
            for device in devices:
                mac = device.get('mac')
                if mac:
                    # Calculate activity level based on packet count
                    packet_count = device.get('packet_count', 0)
                    data_sent = device.get('data_sent', 0)
                    data_received = device.get('data_received', 0)
                    
                    # Determine activity level
                    total_activity = packet_count + (data_sent + data_received) / 1000
                    if total_activity > 1000:
                        activity_level = 'high'
                    elif total_activity > 100:
                        activity_level = 'medium'
                    else:
                        activity_level = 'low'
                    
                    # Map device type
                    device_type = self.map_device_type(device.get('device_type'))
                    
                    self.devices[mac] = {
                        'id': mac,
                        'name': device.get('hostname') or device.get('mac', 'Unknown')[:8],
                        'ip_address': device.get('ip_address', 'N/A'),
                        'type': device_type,
                        'vendor': device.get('vendor', 'Unknown'),
                        'status': device.get('status', 'unknown'),
                        'online': device.get('online', False),
                        'packets_sent': packet_count,
                        'packets_received': device.get('packets_received', 0),
                        'data_sent': data_sent,
                        'data_received': data_received,
                        'activity_level': activity_level,
                        'last_active': device.get('last_seen') or current_time.isoformat(),
                        'first_seen': device.get('first_seen')
                    }
                    
                    # Add to history for timeline
                    self.device_history.append({
                        'timestamp': current_time.isoformat(),
                        'device_mac': mac,
                        'device_name': device.get('hostname') or mac[:8],
                        'event': 'device_active' if device.get('online') else 'device_offline',
                        'details': f"Device {'came online' if device.get('online') else 'went offline'}"
                    })
                    
        except Exception as e:
            print(f"Error updating devices: {e}")
            
    def map_device_type(self, db_type: str | None) -> str:
        mapping = {
            "LAPTOP": "laptop",
            "MOBILE": "mobile",
            "PRINTER": "printer",
            "IOT": "iot",
            "NETWORK": "network"
        }
        return mapping.get(db_type, "network")
    
    def get_device_list(self) -> List[dict]:
        """Get formatted device list for frontend"""
        return list(self.devices.values())
    
    def get_activity_timeline(self) -> List[dict]:
        """Get recent activity timeline"""
        return list(self.device_history)[-20:]  # Last 20 events

# Initialize managers
network_manager = NetworkActivityManager()
device_tracker = DeviceActivityTracker()

@router.websocket("/ws/activity")
async def websocket_activity_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time network activity data"""
    await network_manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client (keepalive or requests)
            data = await websocket.receive_text()
            
            # If client requests data refresh, send latest data
            if data == "get_latest":
                await send_activity_update(websocket)
                
    except WebSocketDisconnect:
        network_manager.disconnect(websocket)

async def send_activity_update(websocket: WebSocket = None):
    """Send comprehensive activity update"""
    
    # Get processed metrics
    processed_data = {}
    if network_manager.last_metrics:
        # Create a mock raw data structure for processing
        mock_raw = {'payload': {'metrics': network_manager.last_metrics}}
        processed_data = network_manager.process_metrics(mock_raw)
    
    # Get device data
    devices = device_tracker.get_device_list()
    timeline = device_tracker.get_activity_timeline()
    
    # Prepare complete response
    response = {
        'type': 'NETWORK_ACTIVITY_UPDATE',
        'timestamp': datetime.now().isoformat(),
        'metrics': processed_data,
        'devices': devices,
        'device_count': len(devices),
        'active_device_count': sum(1 for d in devices if d.get('online')),
        'timeline': timeline,
        'packet_rate_trend': list(network_manager.packet_rate_history)[-10:],  # Last 10 points
        'arp_trend': list(network_manager.arp_history)[-10:]
    }
    
    if websocket:
        await websocket.send_json(response)
    else:
        await network_manager.broadcast_activity_data(response)

# Background task to process incoming data and broadcast updates
async def process_network_data(raw_data: dict):
    """Process incoming network data and broadcast updates"""
    try:
        data_type = raw_data.get('type')
        subtype = raw_data.get('subtype')
        
        if data_type == 'METRIC' and subtype == 'PERIODIC_METRIC_STATE':
            # Process metric data
            processed = network_manager.process_metrics(raw_data)
            await send_activity_update()
            
        elif data_type == 'TOPOLOGY' and subtype == 'PERIODIC_TOPOLOGY_STATE':
            # Update device information
            device_tracker.update_devices(raw_data)
            await send_activity_update()
            
    except Exception as e:
        print(f"Error processing network data: {e}")

# API endpoints for REST fallback
@router.get("/activity/current")
async def get_current_activity():
    """Get current network activity data via REST"""
    processed_data = {}
    if network_manager.last_metrics:
        mock_raw = {'payload': {'metrics': network_manager.last_metrics}}
        processed_data = network_manager.process_metrics(mock_raw)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'metrics': processed_data,
        'devices': device_tracker.get_device_list(),
        'timeline': device_tracker.get_activity_timeline()
    }

@router.get("/activity/history")
async def get_activity_history(minutes: int = 5):
    """Get historical activity data"""
    # Return stored history data
    return {
        'packet_rate_history': list(network_manager.packet_rate_history),
        'arp_history': list(network_manager.arp_history),
        'device_history': list(device_tracker.device_history)
    }

@router.get("/activity/insights")
async def get_activity_insights():
    """Get current network insights"""
    if network_manager.last_metrics:
        mock_raw = {'payload': {'metrics': network_manager.last_metrics}}
        processed = network_manager.process_metrics(mock_raw)
        return {'insights': processed.get('insights', [])}
    return {'insights': []}

# Function to be called when receiving data from your data source
async def receive_network_data(data: dict):
    """Entry point for receiving network data from your data source"""
    await process_network_data(data)

# If you're using a message queue or direct function calls
def handle_incoming_data(data: dict):
    """Synchronous handler for incoming data"""
    asyncio.create_task(process_network_data(data))