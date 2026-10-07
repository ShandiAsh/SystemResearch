import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

def hash_password(password: str) -> str:
    """Hashes a plaintext password using SHA-256 (no external deps)."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plaintext: str, hashed: str) -> bool:
    """Compares a plaintext password against a stored SHA-256 hash."""
    return hashed == hash_password(plaintext)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password = Column(String(128), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), default="ADMIN", nullable=False) # SUPERADMIN, ADMIN, CITIZEN
    email = Column(String(255), nullable=False)
    phone_number = Column(String(32), nullable=True)             # Citizen contact phone (optional)
    barangay = Column(String(64), nullable=True)                 # Citizen's barangay (Mambaling/Pardo)
    assigned_office = Column(String(64), nullable=True)        # Optional specific office scope (e.g. CCDRRMO)
    is_active = Column(String(1), default="1", nullable=False)  # Soft-delete toggle ('1' = active)
    created_at = Column(DateTime, default=utc_now)

    def set_password(self, raw_password: str):
        """Hashes and stores the password for this user."""
        self.password = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Validates a plaintext password against the stored hash."""
        return verify_password(raw_password, self.password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "phone_number": self.phone_number,
            "barangay": self.barangay,
            "assigned_office": self.assigned_office,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(32), unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Categorization & AI Output (5 Sector Categories + 11 Specific Partner Offices)
    category = Column(String(64), nullable=False)           # Assigned Sector Category
    assigned_office = Column(String(64), nullable=True)     # Specific Partner Office (e.g. CCDRRMO, BFP, DEPW)
    predicted_category = Column(String(64), nullable=False) # AI suggestion
    confidence = Column(Float, default=0.0)                  # 0.0 - 1.0
    urgency = Column(String(32), default="MEDIUM")          # CRITICAL, HIGH, MEDIUM, LOW
    multimodal_breakdown = Column(Text, default="{}")        # JSON breakdown of text/image weights
    
    # Status Lifecycle
    # PENDING_REVIEW, VERIFIED, DISPATCHED, IN_PROGRESS, RESOLVED, FLAGGED
    status = Column(String(32), default="PENDING_REVIEW", index=True)
    
    # Media & Forensic Metadata
    photo_filename = Column(String(255), nullable=True)
    exif_data = Column(Text, default="{}")                  # Raw EXIF JSON (Camera, Date, Tags)
    
    # Geolocation & Verification
    citizen_lat = Column(Float, nullable=True)              # From browser/device navigator.geolocation
    citizen_lon = Column(Float, nullable=True)
    exif_lat = Column(Float, nullable=True)                 # From photo EXIF GPSInfo
    exif_lon = Column(Float, nullable=True)
    gps_distance_m = Column(Float, nullable=True)           # Delta in meters
    
    # VERIFIED_GENUINE, GPS_DISCREPANCY_FLAGGED, EXIF_MISSING_FALLBACK_ACTIVE, UNVERIFIABLE
    verification_status = Column(String(64), default="UNVERIFIABLE", index=True)
    verification_notes = Column(Text, default="")
    address = Column(String(255), default="Unknown Location")
    
    # Citizen Info
    citizen_name = Column(String(128), default="Anonymous Citizen")
    citizen_contact = Column(String(128), default="N/A")
    
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    notifications = relationship("NotificationLog", back_populates="report", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "assigned_office": self.assigned_office,
            "predicted_category": self.predicted_category,
            "confidence": round(self.confidence, 4),
            "urgency": self.urgency,
            "multimodal_breakdown": self.multimodal_breakdown,
            "status": self.status,
            "photo_filename": self.photo_filename,
            "photo_url": f"/static/images/uploads/{self.photo_filename}" if self.photo_filename else None,
            "exif_data": self.exif_data,
            "citizen_lat": self.citizen_lat,
            "citizen_lon": self.citizen_lon,
            "exif_lat": self.exif_lat,
            "exif_lon": self.exif_lon,
            "gps_distance_m": round(self.gps_distance_m, 2) if self.gps_distance_m is not None else None,
            "verification_status": self.verification_status,
            "verification_notes": self.verification_notes,
            "address": self.address,
            "citizen_name": self.citizen_name,
            "citizen_contact": self.citizen_contact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    recipient_sector = Column(String(64), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    status = Column(String(32), default="SIMULATED")  # SENT, SIMULATED, FAILED
    sent_at = Column(DateTime, default=utc_now)

    report = relationship("Report", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "recipient_sector": self.recipient_sector,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "body_html": self.body_html,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
