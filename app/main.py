import os
import uuid
import json
import shutil
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

import logging

logger = logging.getLogger("tugon.main")

from app.config import BASE_DIR, UPLOAD_DIR, SECTORS, SECTOR_CATEGORIES, PARTNER_OFFICES
from app.database import engine, get_db, init_db
from app.models import Report, NotificationLog
from app.models import Report, NotificationLog, User
from app.verifier import extract_exif_data, verify_geolocation, reverse_geocode
from app.classifier import classifier
from app.notifier import dispatch_sector_notification
from app.seeder import seed_sample_reports

# Initialize FastAPI app
app = FastAPI(
    title="TUGON AI - Intelligent Municipal Reporting & Verification System",
    description="Multimodal Classification, EXIF/GPS Forensic Verification, and Automated Municipal Sector Dispatch API",
    version="1.0.0"
)

# Enable CORS for mobile and cross-origin frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory for custom CSS, JavaScript, and user uploads
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    """Initialize database and seed initial sample incident reports."""
    init_db()
    with Session(engine) as db:
        seed_sample_reports(db)


# ==========================================
# Frontend Page Routes
# ==========================================

@app.get("/")
def serve_landing_page(request: Request):
    """Starter / landing page — entry point for both citizens and admins."""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/portal")
def serve_citizen_portal(request: Request):
    """Citizen Mobile & Web Incident Reporting Interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "sectors": SECTORS
    })


@app.get("/citizen/login")
def serve_citizen_login(request: Request):
    """Citizen login page."""
    return templates.TemplateResponse("citizen_login.html", {"request": request})


@app.get("/citizen/register")
def serve_citizen_register(request: Request):
    """Citizen registration page."""
    return templates.TemplateResponse("citizen_register.html", {"request": request})


@app.get("/citizen/profile")
def serve_citizen_profile(request: Request):
    """Citizen profile page."""
    return templates.TemplateResponse("citizen_profile.html", {"request": request})


@app.get("/citizen/dashboard")
def serve_citizen_dashboard(request: Request):
    """Citizen dashboard — calamity drill guide, emergency hotlines, and submitted reports."""
    return templates.TemplateResponse("citizen_dashboard.html", {"request": request})


@app.get("/dashboard")
def serve_admin_dashboard(request: Request):
    """Command Dashboard for Municipal Admins and Partner Sectors."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "sectors": SECTORS
    })


@app.get("/login")
def serve_login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
def serve_register_page(request: Request):
    """Admin registration page."""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "offices": PARTNER_OFFICES
    })


# ==========================================
# REST API Endpoints
# ==========================================

@app.get("/api/sectors")
def get_sectors():
    """Returns directory of active sector categories and their specific partner offices."""
    return {
        "categories": SECTOR_CATEGORIES,
        "offices": PARTNER_OFFICES
    }


@app.post("/api/auth/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Admin & Superadmin Authentication endpoint."""
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or (not user.check_password(password) and user.password != password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin or Superadmin credentials."
        )
    return {
        "success": True,
        "message": f"Authenticated successfully as {user.role}",
        "user": user.to_dict()
    }


@app.post("/api/auth/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form("ADMIN"),
    assigned_office: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Registers a new administrator or superadmin account."""
    existing = db.query(User).filter(User.username == username.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already taken."
        )
    if role not in ("ADMIN", "SUPERADMIN"):
        role = "ADMIN"
    if assigned_office and assigned_office not in PARTNER_OFFICES:
        assigned_office = None

    new_user = User(
        username=username.strip(),
        full_name=full_name.strip(),
        role=role,
        email=email.strip(),
        assigned_office=assigned_office
    )
    new_user.set_password(password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"[+] New {role} user registered: {new_user.username}")
    return {
        "success": True,
        "message": f"Account created successfully as {role}: {new_user.username}",
        "user": new_user.to_dict()
    }


@app.post("/api/citizen/auth/register")
def citizen_register(
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    barangay: str = Form(...),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Registers a new citizen account for the TUGON AI reporting portal."""
    existing = db.query(User).filter(User.username == username.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already taken."
        )

    if not phone_number or len(phone_number) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid mobile number is required."
        )

    if barangay not in ("Mambaling", "Pardo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Barangay must be Mambaling or Pardo."
        )

    new_user = User(
        username=username.strip(),
        full_name=full_name.strip(),
        role="CITIZEN",
        email=email.strip() if email else "",
        phone_number=phone_number.strip(),
        barangay=barangay,
        assigned_office=None
    )
    new_user.set_password(password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"[+] New CITIZEN user registered: {new_user.username} ({new_user.barangay})")
    return {
        "success": True,
        "message": f"Citizen account created successfully: {new_user.username}",
        "user": new_user.to_dict()
    }


@app.post("/api/citizen/auth/login")
def citizen_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Citizen authentication endpoint for portal access."""
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or user.role != "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid citizen credentials or account not found."
        )
    if not user.check_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid citizen credentials."
        )
    return {
        "success": True,
        "message": f"Welcome, {user.full_name}!",
        "user": user.to_dict()
    }


@app.get("/api/citizen/profile")
def get_citizen_profile(
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Returns a citizen's profile. Uses user_id from the authenticated session (stored in localStorage)."""
    user = db.query(User).filter(User.id == user_id, User.role == "CITIZEN").first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizen user not found."
        )
    reports_count = db.query(Report).filter(Report.citizen_name == user.full_name).count()
    user_dict = user.to_dict()
    user_dict["reports_count"] = reports_count
    return {"user": user_dict}


@app.put("/api/citizen/profile")
def update_citizen_profile(
    user_id: int = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    barangay: str = Form(...),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Updates a citizen's profile information."""
    user = db.query(User).filter(User.id == user_id, User.role == "CITIZEN").first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizen user not found."
        )
    user.full_name = full_name.strip()
    user.phone_number = phone_number.strip()
    if barangay not in ("Mambaling", "Pardo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Barangay must be Mambaling or Pardo."
        )
    user.barangay = barangay
    user.email = (email or "").strip()

    if password:
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters."
            )
        user.set_password(password)

    db.commit()
    db.refresh(user)

    logger.info(f"[*] Citizen profile updated: {user.username}")
    return {"success": True, "message": "Profile updated successfully.", "user": user.to_dict()}


@app.get("/api/auth/users")
def list_users(db: Session = Depends(get_db)):
    """Superadmin endpoint: List all System Administrators."""
    users = db.query(User).all()
    return [u.to_dict() for u in users]


@app.post("/api/analyze-preview")
async def analyze_preview(
    title: str = Form(""),
    description: str = Form(""),
    photo: Optional[UploadFile] = File(None)
):
    """
    Live AI multimodal analysis & EXIF preview endpoint.
    Called dynamically by the frontend as citizens fill out the report form.
    """
    saved_temp_path = None
    exif_info = {"has_exif": False, "lat": None, "lon": None}

    if photo and photo.filename:
        # Save temporary file for analysis
        temp_filename = f"temp_{uuid.uuid4().hex[:8]}_{photo.filename}"
        saved_temp_path = UPLOAD_DIR / temp_filename
        with open(saved_temp_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        # Extract EXIF
        exif_info = extract_exif_data(str(saved_temp_path))

    # Run AI prediction
    ai_result = classifier.predict(title, description, str(saved_temp_path) if saved_temp_path else None)

    # Clean up temp file if needed
    if saved_temp_path and os.path.exists(saved_temp_path):
        try:
            os.remove(saved_temp_path)
        except Exception:
            pass

    assigned_office = ai_result.get("assigned_office")
    return {
        "classification": ai_result,
        "exif_metadata": exif_info,
        "sector_meta": SECTOR_CATEGORIES.get(ai_result["predicted_sector"], {}),
        "office_meta": PARTNER_OFFICES.get(assigned_office, {}) if assigned_office else {}
    }


@app.post("/api/reports")
async def submit_report(
    title: str = Form(...),
    description: str = Form(...),
    citizen_lat: Optional[float] = Form(None),
    citizen_lon: Optional[float] = Form(None),
    citizen_name: Optional[str] = Form("Anonymous Citizen"),
    citizen_contact: Optional[str] = Form("N/A"),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Citizen report submission endpoint.
    Processes: Photo upload, EXIF extraction, Multimodal AI triage, GPS geofencing, DB storage, and notification.
    """
    photo_filename = None
    exif_info = {"has_exif": False, "lat": None, "lon": None}
    image_full_path = None

    if photo and photo.filename:
        # Generate secure filename with timestamp
        ext = Path(photo.filename).suffix.lower()
        if not ext:
            ext = ".jpg"
        photo_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        image_full_path = UPLOAD_DIR / photo_filename

        with open(image_full_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        # 1. Extract EXIF data
        exif_info = extract_exif_data(str(image_full_path))

    # 2. Multimodal AI Classification (Tagalog/English NLP + Vision Heuristics)
    ai_result = classifier.predict(
        title=title,
        description=description,
        image_path=str(image_full_path) if image_full_path else None
    )

    # 3. GPS Cross-Verification (EXIF vs Citizen Device Geolocation)
    verif = verify_geolocation(
        exif_lat=exif_info.get("lat"),
        exif_lon=exif_info.get("lon"),
        device_lat=citizen_lat,
        device_lon=citizen_lon
    )

    # 4. Resolve Address
    target_lat = verif["final_lat"] or citizen_lat
    target_lon = verif["final_lon"] or citizen_lon
    address = reverse_geocode(target_lat, target_lon)

    # 5. Determine Report Lifecycle Status
    if verif["status"] == "GPS_DISCREPANCY_FLAGGED":
        report_status = "FLAGGED"
    elif ai_result["urgency"] == "CRITICAL":
        report_status = "DISPATCHED"
    else:
        report_status = "VERIFIED"

    # Generate sequential ticket number
    count = db.query(Report).count() + 1
    ticket_number = f"TUGON-{datetime.now(timezone.utc).year}-{count:04d}"

    # 6. Save to Database
    report = Report(
        ticket_number=ticket_number,
        title=title,
        description=description,
        category=ai_result["predicted_sector"],
        predicted_category=ai_result["predicted_sector"],
        assigned_office=ai_result.get("assigned_office"),
        confidence=ai_result["confidence"],
        urgency=ai_result["urgency"],
        multimodal_breakdown=json.dumps({
            "keywords": ai_result["matched_keywords"],
            "visual_cues": ai_result["visual_cues"],
            "fused_dist": ai_result["fused_distribution"],
            "requirements": ai_result.get("requirements", []),
            "react_trace": ai_result.get("react_trace", [])
        }),
        status=report_status,
        photo_filename=photo_filename,
        exif_data=json.dumps(exif_info),
        citizen_lat=citizen_lat,
        citizen_lon=citizen_lon,
        exif_lat=exif_info.get("lat"),
        exif_lon=exif_info.get("lon"),
        gps_distance_m=verif["distance_m"],
        verification_status=verif["status"],
        verification_notes=verif["notes"],
        address=address,
        citizen_name=citizen_name or "Anonymous Citizen",
        citizen_contact=citizen_contact or "N/A"
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    # 7. Automated Email Dispatch to Municipal Sector
    notification = None
    if report_status in ("DISPATCHED", "VERIFIED"):
        notification = dispatch_sector_notification(db, report)

    return {
        "success": True,
        "message": "Incident report submitted and analyzed successfully.",
        "report": report.to_dict(),
        "dispatched_notification": notification.to_dict() if notification else None
    }


@app.get("/api/reports")
def list_reports(
    sector: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    verif_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns list of reports with optional sector, status, and forensic filters."""
    query = db.query(Report)

    if sector and sector != "ALL":
        query = query.filter(Report.category == sector)
    if status and status != "ALL":
        query = query.filter(Report.status == status)
    if urgency and urgency != "ALL":
        query = query.filter(Report.urgency == urgency)
    if verif_status and verif_status != "ALL":
        query = query.filter(Report.verification_status == verif_status)

    reports = query.order_by(desc(Report.created_at)).all()
    return [r.to_dict() for r in reports]


@app.get("/api/citizen/reports")
def list_citizen_reports(
    citizen_name: str = None,
    db: Session = Depends(get_db)
):
    """Returns reports submitted by a specific citizen (for the citizen dashboard)."""
    if not citizen_name:
        return []
    reports = db.query(Report).filter(Report.citizen_name == citizen_name).order_by(desc(Report.created_at)).all()
    return [r.to_dict() for r in reports]


@app.put("/api/citizen/reports/{report_id}")
def correct_citizen_report(
    report_id: int,
    citizen_name: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    correction_note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Allows citizen to correct misinformation in their own report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Verify the citizen owns this report
    if report.citizen_name != citizen_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own reports."
        )

    old_title = report.title
    old_desc = report.description
    report.title = title.strip()
    report.description = description.strip()
    report.updated_at = datetime.now(timezone.utc)

    # Log the correction in verification_notes
    note = f"[Citizen Correction]: {correction_note or 'No reason provided.'}"
    if old_title != report.title or old_desc != report.description:
        report.verification_notes = f"{report.verification_notes}\n{note}\n- Title: '{old_title}' -> '{report.title}'\n- Description updated".strip()

    db.commit()
    db.refresh(report)

    logger.info(f"[*] Citizen correction on report {report.ticket_number} by {citizen_name}")
    return {"success": True, "message": "Report corrected successfully.", "report": report.to_dict()}


@app.get("/api/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Retrieve single report with full forensic metadata and notification history."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    result = report.to_dict()
    result["notifications"] = [n.to_dict() for n in report.notifications]
    return result


@app.patch("/api/reports/{report_id}/status")
def update_report_status(
    report_id: int,
    new_status: str = Form(...),
    assigned_sector: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Admin endpoint to update report status (e.g. In Progress, Resolved) and re-assign sector."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = new_status
    if assigned_sector and (assigned_sector in SECTOR_CATEGORIES or assigned_sector in PARTNER_OFFICES):
        report.category = assigned_sector
        # Also update assigned_office if it's a specific office key
        if assigned_sector in PARTNER_OFFICES:
            report.assigned_office = assigned_sector

    if notes:
        report.verification_notes = f"{report.verification_notes}\n[Admin Update]: {notes}".strip()

    report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)

    return {"success": True, "report": report.to_dict()}


@app.post("/api/reports/{report_id}/dispatch")
def trigger_dispatch(
    report_id: int,
    target_sector: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Manually triggers or re-sends sector alert email."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    sector_to_use = target_sector or report.category
    notification = dispatch_sector_notification(db, report, sector_to_use)
    
    # Update status to DISPATCHED if it was pending
    if report.status in ("PENDING_REVIEW", "VERIFIED"):
        report.status = "DISPATCHED"
        db.commit()
        db.refresh(report)

    return {
        "success": True,
        "message": f"Alert email dispatched to {sector_to_use}",
        "notification": notification.to_dict()
    }


@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Computes real-time incident analytics and verification tally for dashboards."""
    reports = db.query(Report).all()

    total = len(reports)
    verified = sum(1 for r in reports if r.verification_status == "VERIFIED_GENUINE")
    flagged = sum(1 for r in reports if r.verification_status == "GPS_DISCREPANCY_FLAGGED")
    fallback = sum(1 for r in reports if r.verification_status == "EXIF_MISSING_FALLBACK_ACTIVE")
    resolved = sum(1 for r in reports if r.status == "RESOLVED")
    dispatched = sum(1 for r in reports if r.status == "DISPATCHED")

    # Sector category distribution (5 categories)
    sector_counts = {sec: 0 for sec in SECTOR_CATEGORIES.keys()}
    for r in reports:
        if r.category in sector_counts:
            sector_counts[r.category] += 1
        elif r.category:
            sector_counts[r.category] = 1

    # Office-level distribution (11 specific offices)
    office_counts = {office: 0 for office in PARTNER_OFFICES.keys()}
    for r in reports:
        office = getattr(r, "assigned_office", None)
        if office and office in office_counts:
            office_counts[office] += 1
        elif office:
            office_counts[office] = 1

    # Urgency distribution
    urgency_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in reports:
        if r.urgency in urgency_counts:
            urgency_counts[r.urgency] += 1

    return {
        "total_reports": total,
        "verified_genuine": verified,
        "gps_flagged": flagged,
        "fallback_active": fallback,
        "dispatched_active": dispatched,
        "resolved": resolved,
        "sector_breakdown": sector_counts,
        "office_breakdown": office_counts,
        "urgency_breakdown": urgency_counts,
        "sectors_meta": SECTOR_CATEGORIES,
        "offices_meta": PARTNER_OFFICES
    }


@app.get("/api/analytics/superadmin")
def get_superadmin_analysis(
    role: str = Query(..., description="Must be SUPERADMIN"),
    db: Session = Depends(get_db)
):
    """SUPERADMIN-ONLY endpoint: Detailed report analysis with verification forensics,
    AI confidence scoring trends, and anomaly detection.

    The 'role' query parameter must be 'SUPERADMIN' — citizens and regular admins
    cannot access this endpoint.
    """
    if role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — Superadmin privileges required."
        )

    reports = db.query(Report).all()

    # Per-sector performance & verification analytics
    sector_analysis = {}
    for cat_key, cat_name in SECTOR_CATEGORIES.items():
        sector_reports = [r for r in reports if r.category == cat_key]
        if not sector_reports:
            continue
        verified = sum(1 for r in sector_reports if r.verification_status == "VERIFIED_GENUINE")
        flagged = sum(1 for r in sector_reports if r.verification_status == "GPS_DISCREPANCY_FLAGGED")
        avg_conf = sum(r.confidence for r in sector_reports) / len(sector_reports)
        sector_analysis[cat_key] = {
            "sector_name": cat_name,
            "total_reports": len(sector_reports),
            "verified_genuine": verified,
            "gps_flagged": flagged,
            "avg_ai_confidence": round(avg_conf, 4),
            "resolved": sum(1 for r in sector_reports if r.status == "RESOLVED"),
            "avg_resolution_days": round(
                sum(
                    (r.updated_at - r.created_at).total_seconds() / 86400
                    for r in sector_reports if r.status == "RESOLVED" and r.created_at and r.updated_at
                ) / max(1, sum(1 for r in sector_reports if r.status == "RESOLVED" and r.created_at and r.updated_at)),
                2
            ) if any(r.status == "RESOLVED" and r.created_at and r.updated_at for r in sector_reports) else 0,
        }

    # AI confidence scoring distribution
    confidence_buckets = {"0-25%": 0, "26-50%": 0, "51-75%": 0, "76-100%": 0}
    for r in reports:
        pct = int(r.confidence * 100) if r.confidence else 0
        if pct <= 25:
            confidence_buckets["0-25%"] += 1
        elif pct <= 50:
            confidence_buckets["26-50%"] += 1
        elif pct <= 75:
            confidence_buckets["51-75%"] += 1
        else:
            confidence_buckets["76-100%"] += 1

    # Anomaly detection: reports with GPS discrepancies or low confidence
    anomalies = [
        r.to_dict() for r in reports
        if r.verification_status == "GPS_DISCREPANCY_FLAGGED"
        or (r.confidence is not None and r.confidence < 0.5)
    ]

    # False report rate (flagged / total)
    false_report_rate = round(
        sum(1 for r in reports if r.verification_status == "GPS_DISCREPANCY_FLAGGED") / max(1, len(reports)) * 100, 2
    )

    return {
        "is_superadmin_only": True,
        "total_reports": len(reports),
        "sector_analysis": sector_analysis,
        "confidence_distribution": confidence_buckets,
        "anomalies": anomalies,
        "false_report_rate_pct": false_report_rate,
        "verification_breakdown": {
            "VERIFIED_GENUINE": sum(1 for r in reports if r.verification_status == "VERIFIED_GENUINE"),
            "GPS_DISCREPANCY_FLAGGED": sum(1 for r in reports if r.verification_status == "GPS_DISCREPANCY_FLAGGED"),
            "EXIF_MISSING_FALLBACK_ACTIVE": sum(1 for r in reports if r.verification_status == "EXIF_MISSING_FALLBACK_ACTIVE"),
        },
        "status_breakdown": {
            "PENDING_REVIEW": sum(1 for r in reports if r.status == "PENDING_REVIEW"),
            "VERIFIED": sum(1 for r in reports if r.status == "VERIFIED"),
            "DISPATCHED": sum(1 for r in reports if r.status == "DISPATCHED"),
            "IN_PROGRESS": sum(1 for r in reports if r.status == "IN_PROGRESS"),
            "RESOLVED": sum(1 for r in reports if r.status == "RESOLVED"),
        },
    }


@app.get("/api/notifications")
def list_notifications(limit: int = 50, db: Session = Depends(get_db)):
    """Returns log of all automated sector dispatch alerts."""
    logs = db.query(NotificationLog).order_by(desc(NotificationLog.sent_at)).limit(limit).all()
    return [l.to_dict() for l in logs]
