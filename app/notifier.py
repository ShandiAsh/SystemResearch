import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SIMULATE_EMAIL, SECTOR_CATEGORIES, PARTNER_OFFICES
)
from app.models import Report, NotificationLog

logger = logging.getLogger("tugon.notifier")


def _resolve_office_info(report: Report, fallback_key: Optional[str] = None) -> dict:
    """
    Resolves the partner office metadata dict to use in notifications.
    Priority: report.assigned_office → fallback_key (as office) → generic fallback.
    """
    # 1. Use specific assigned office if available
    office_key = getattr(report, "assigned_office", None) or fallback_key
    if office_key and office_key in PARTNER_OFFICES:
        return {"office_key": office_key, **PARTNER_OFFICES[office_key]}

    # 2. Fall back to category-level lookup (pick first office of category)
    category_key = getattr(report, "category", None) or fallback_key
    if category_key and category_key in SECTOR_CATEGORIES:
        cat = SECTOR_CATEGORIES[category_key]
        first_office_key = cat.get("offices", [None])[0]
        if first_office_key and first_office_key in PARTNER_OFFICES:
            return {"office_key": first_office_key, **PARTNER_OFFICES[first_office_key]}

    # 3. Ultimate fallback
    return {
        "office_key": office_key or "UNKNOWN",
        "name": office_key or "Municipal Dispatch",
        "short_name": office_key or "Dispatch",
        "email": "dispatch.generic@cebucity.gov.ph.mock",
        "color": "#3b82f6",
        "description": "General municipal incident response",
        "icon": "fa-shield-halved"
    }


def generate_html_email(report: Report, office_key: Optional[str] = None) -> str:
    """
    Generates a responsive, official municipal emergency dispatch email template.
    Uses PARTNER_OFFICES metadata for the assigned government office details.
    """
    office_info = _resolve_office_info(report, office_key)

    urgency_color = {
        "CRITICAL": "#ef4444",
        "HIGH": "#f59e0b",
        "MEDIUM": "#3b82f6",
        "LOW": "#10b981"
    }.get(report.urgency, "#6b7280")

    verif_badge_color = {
        "VERIFIED_GENUINE": "#10b981",
        "GPS_DISCREPANCY_FLAGGED": "#ef4444",
        "EXIF_MISSING_FALLBACK_ACTIVE": "#f59e0b",
        "UNVERIFIABLE": "#6b7280"
    }.get(report.verification_status, "#6b7280")

    map_lat = report.exif_lat if report.exif_lat else report.citizen_lat
    map_lon = report.exif_lon if report.exif_lon else report.citizen_lon
    map_link = f"https://www.google.com/maps/search/?api=1&query={map_lat},{map_lon}" if map_lat and map_lon else "#"

    office_color = office_info.get("color", "#3b82f6")
    office_name = office_info.get("name", office_info.get("office_key", "Municipal Dispatch"))
    office_desc = office_info.get("description", "")
    short_name = office_info.get("short_name", office_name)

    # Resolve the sector category label for the email header
    category_key = getattr(report, "category", None)
    category_label = ""
    if category_key and category_key in SECTOR_CATEGORIES:
        category_label = SECTOR_CATEGORIES[category_key].get("name", category_key)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
        .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 24px; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; letter-spacing: 0.5px; }}
        .header .badge {{ display: inline-block; background: {urgency_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; margin-top: 8px; text-transform: uppercase; }}
        .content {{ padding: 24px; }}
        .field-group {{ margin-bottom: 16px; }}
        .label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
        .value {{ font-size: 15px; color: #0f172a; font-weight: 500; }}
        .alert-box {{ background: #f8fafc; border-left: 4px solid {office_color}; padding: 12px 16px; border-radius: 4px; margin: 16px 0; }}
        .forensic-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; padding: 14px; border-radius: 8px; margin-top: 16px; }}
        .flagged-box {{ background: #fef2f2; border: 1px solid #fecaca; padding: 14px; border-radius: 8px; margin-top: 16px; }}
        .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 12px; }}
        .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 TUGON AI Municipal Incident Dispatch</h1>
            <div class="badge">{report.urgency} PRIORITY INCIDENT</div>
        </div>
        <div class="content">
            <div class="field-group">
                <div class="label">Incident Ticket ID</div>
                <div class="value" style="font-family: monospace; font-size: 16px; font-weight: 700; color: #2563eb;">{report.ticket_number}</div>
            </div>

            <div class="alert-box">
                <div class="label" style="color: {office_color};">Assigned Partner Government Office</div>
                <div class="value" style="font-size: 16px; font-weight: 700;">{office_name}</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">{office_desc}</div>
                {f'<div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">Sector Category: {category_label}</div>' if category_label else ''}
            </div>

            <div class="field-group">
                <div class="label">Incident Title &amp; Citizen Description</div>
                <div class="value" style="font-weight: 700; margin-bottom: 4px;">{report.title}</div>
                <div class="value" style="font-size: 14px; color: #334155; line-height: 1.5; background: #f8fafc; padding: 10px; border-radius: 6px;">
                    "{report.description}"
                </div>
            </div>

            <div class="field-group">
                <div class="label">Location &amp; Reverse Geocode</div>
                <div class="value">{report.address}</div>
                <div style="font-size: 12px; color: #64748b;">Coordinates: {map_lat or 'N/A'}, {map_lon or 'N/A'}</div>
            </div>

            <div class="{ 'flagged-box' if 'FLAGGED' in report.verification_status else 'forensic-box' }">
                <div class="label" style="color: {verif_badge_color};">EXIF / GPS Verification Forensic Audit</div>
                <div class="value" style="font-size: 13px; font-weight: 600; color: {verif_badge_color};">
                    Status: {report.verification_status}
                </div>
                <div style="font-size: 12px; color: #475569; margin-top: 4px;">
                    {report.verification_notes}
                </div>
                {f'<div style="font-size: 11px; color: #64748b; margin-top: 4px;">Haversine Delta: {report.gps_distance_m:.1f} meters</div>' if report.gps_distance_m is not None else ''}
            </div>

            <div class="field-group" style="margin-top: 16px;">
                <div class="label">AI Multimodal Rationale</div>
                <div style="font-size: 13px; color: #334155;">
                    Confidence Score: <strong>{int(report.confidence * 100)}%</strong> | Urgency: <strong>{report.urgency}</strong>
                </div>
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="{map_link}" class="btn" target="_blank">📍 Open in Google Maps</a>
            </div>
        </div>
        <div class="footer">
            Automated Alert generated by TUGON AI Capstone Incident Response System.<br>
            Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
    </div>
</body>
</html>
"""
    return html


def dispatch_sector_notification(db: Session, report: Report, target_office: Optional[str] = None) -> NotificationLog:
    """
    Dispatches automated notification email to the assigned partner government office.
    Resolves recipient from PARTNER_OFFICES using report.assigned_office.
    Records log entry in SQLite/Postgres.
    """
    office_info = _resolve_office_info(report, target_office)
    office_key = office_info.get("office_key", "UNKNOWN")
    recipient_email = office_info.get("email", "dispatch.generic@cebucity.gov.ph.mock")

    subject = f"[{report.urgency}] TUGON Incident Alert: {report.ticket_number} - {report.title}"
    body_html = generate_html_email(report, office_key)

    status = "SIMULATED"

    # Attempt live SMTP if credentials are provided and simulation is disabled
    if not SIMULATE_EMAIL and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = recipient_email
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, recipient_email, msg.as_string())
            status = "SENT"
            logger.info(f"Live email alert dispatched to {recipient_email} for {report.ticket_number}")
        except Exception as e:
            logger.error(f"Failed live SMTP transmission: {e}. Falling back to logged simulation.")
            status = "FAILED"
    else:
        logger.info(f"[SIMULATED NOTIFICATION] Dispatched to {office_info.get('name', office_key)} <{recipient_email}> for {report.ticket_number}")
        status = "SIMULATED"

    # Save to database log
    log_entry = NotificationLog(
        report_id=report.id,
        recipient_sector=office_key,
        recipient_email=recipient_email,
        subject=subject,
        body_html=body_html,
        status=status,
        sent_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry
