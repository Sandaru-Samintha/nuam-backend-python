from sqlalchemy import Column, String, DateTime, Integer, Boolean, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)  # MAC address
    hostname = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    os = Column(String, nullable=True)
    vendor = Column(String, nullable=True)

    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)

    status = Column(String, default="active")  # active / idle / left
    online = Column(Boolean, default=True)
    active = Column(Boolean, default=True)

    # Traffic data
    data_sent = Column(BigInteger, default=0)      # bytes
    data_received = Column(BigInteger, default=0)  # bytes
    packet_count = Column(Integer, default=0)

    # Optional metrics from payload
    access_logs = Column(String, nullable=True)
    access_services = Column(String, nullable=True)  

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())