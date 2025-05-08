\
from sqlalchemy import Column, Integer, String, DateTime, Time, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class StoreStatus(Base):
    __tablename__ = "store_status"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, index=True)
    timestamp_utc = Column(DateTime, index=True)
    status = Column(String) 

class BusinessHours(Base):
    __tablename__ = "business_hours"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, index=True)
    day_of_week = Column(Integer, index=True) 
    start_time_local = Column(Time)
    end_time_local = Column(Time)

class StoreTimezone(Base):
    __tablename__ = "store_timezone"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, unique=True, index=True)
    timezone_str = Column(String, default="America/Chicago")

class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="Running")
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ReportData(Base):
    __tablename__ = "report_data"
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"))
    store_id = Column(String, index=True)
    uptime_last_hour = Column(Float) 
    uptime_last_day = Column(Float) 
    uptime_last_week = Column(Float) 
    downtime_last_hour = Column(Float) 
    downtime_last_day = Column(Float) 
    downtime_last_week = Column(Float)
    report = relationship("Report")
