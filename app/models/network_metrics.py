from sqlalchemy import Column, Integer, BigInteger, DateTime
from app.core.database import Base

class NetworkMetric(Base):
    __tablename__ = "network_metrics"

    id = Column(Integer, primary_key=True, index=True)
    measure_time = Column(DateTime)

    total_devices = Column(Integer)
    active_devices = Column(Integer)

    data_sent = Column(BigInteger)        # bytes
    data_received = Column(BigInteger)    # bytes

    total_packets = Column(Integer)
    total_broadcast_packets = Column(Integer, default=0)
    total_unicast_packets = Column(Integer, default=0)
    ip_packets = Column(Integer, default=0)
    tcp_packets = Column(Integer, default=0)
    udp_packets = Column(Integer, default=0)
    icmp_packets = Column(Integer, default=0)

    arp_requests = Column(Integer, default=0)
    arp_replies = Column(Integer, default=0)

    dns_queries = Column(Integer, default=0)
    dhcp_packets = Column(Integer, default=0)
    http_requests = Column(Integer, default=0)
    tls_handshakes = Column(Integer, default=0)