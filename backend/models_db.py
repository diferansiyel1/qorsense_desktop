"""
QorSense Multi-Tenant Database Models

This module defines the SQLAlchemy ORM models for the multi-tenant architecture.
Supports organizations, users with role-based access, and sensor data management.
"""

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, 
    Enum, JSON, Text, Boolean
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum
import uuid
from datetime import datetime


# ==============================================================================
# ENUMS
# ==============================================================================

class Role(str, enum.Enum):
    """
    Multi-tenant role enumeration for access control.
    
    - SUPER_ADMIN: Platform-wide administrative access
    - ORG_ADMIN: Organization-level administrative access
    - ENGINEER: Technical user with analysis capabilities
    """
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    ENGINEER = "engineer"


class SourceType(str, enum.Enum):
    """Sensor data source type enumeration."""
    CSV = "CSV"
    SCADA = "SCADA"
    IoT = "IoT"


# Legacy enum - kept for backward compatibility during migration
class UserRole(str, enum.Enum):
    """User role enumeration (deprecated - use Role instead)."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ENGINEER = "engineer"
    ADMIN = "admin"


# ==============================================================================
# MULTI-TENANT MODELS
# ==============================================================================

class Organization(Base):
    """
    Organization model for multi-tenant architecture.
    
    Each organization represents a separate tenant with isolated data access.
    """
    __tablename__ = "organizations"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    name = Column(String(255), unique=True, index=True, nullable=False)
    subscription_plan = Column(String(50), default="Free")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sensors = relationship("Sensor", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"


class User(Base):
    """
    User model for authentication and authorization.
    
    Users belong to an organization and have role-based access control.
    """
    __tablename__ = "users"
    
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.ENGINEER, nullable=False)
    organization_id = Column(
        String(36), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=True,
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


# ==============================================================================
# SENSOR & ANALYSIS MODELS
# ==============================================================================

class Sensor(Base):
    """
    Sensor model with multi-tenant support.
    
    Each sensor belongs to an organization and can have multiple readings
    and analysis results associated with it.
    """
    __tablename__ = "sensors"

    id = Column(String(50), primary_key=True, index=True)  # Hardware ID (e.g., 'pH-01')
    organization_id = Column(
        String(36), 
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    source_type = Column(Enum(SourceType), default=SourceType.CSV)
    config = Column(JSON, nullable=True)  # For SCADA IP/Protocol details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor", cascade="all, delete-orphan")
    analyses = relationship("AnalysisResultDB", back_populates="sensor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sensor(id={self.id}, name={self.name}, org={self.organization_id})>"


class SensorReading(Base):
    """
    Sensor reading model for time-series data storage.
    
    Stores individual sensor measurements with timestamps.
    """
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(
        String(50), 
        ForeignKey("sensors.id", ondelete="CASCADE"), 
        index=True,
        nullable=False
    )
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    value = Column(Float, nullable=False)

    # Relationships
    sensor = relationship("Sensor", back_populates="readings")

    def __repr__(self):
        return f"<SensorReading(id={self.id}, sensor={self.sensor_id}, value={self.value})>"


class AnalysisResultDB(Base):
    """
    Analysis result model for storing sensor health analysis outcomes.
    
    Contains health scores, diagnostic metrics, and recommendations.
    """
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(
        String(50), 
        ForeignKey("sensors.id", ondelete="CASCADE"), 
        index=True,
        nullable=False
    )
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    health_score = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)  # 'Normal', 'Warning', 'Critical', 'Unknown'
    metrics = Column(JSON, nullable=True)  # Stores bias, slope, hysteresis curves, etc.
    diagnosis = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    # Relationships
    sensor = relationship("Sensor", back_populates="analyses")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, sensor={self.sensor_id}, score={self.health_score})>"
