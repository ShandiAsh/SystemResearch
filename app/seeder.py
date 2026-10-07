import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Report, NotificationLog
from app.models import Report, NotificationLog, User, hash_password
from app.config import SECTORS
from app.verifier import verify_geolocation, reverse_geocode
from app.classifier import classifier
from app.notifier import dispatch_sector_notification

def seed_sample_reports(db: Session, force_reseed: bool = False):
    """
    Seeds initial realistic reports calibrated exclusively for Cebu City (focusing on Mambaling & Pardo), Philippines.
    Also seeds default Superadmin and Admin accounts.
    """
    # 1. Seed Admin and Superadmin Users
    if db.query(User).count() == 0 or force_reseed:
        if force_reseed:
            db.query(User).delete()
            db.commit()

        superadmin = User(
            username="superadmin",
            password=hash_password("admin123"),
            full_name="Cebu City Super Administrator",
            role="SUPERADMIN",
            email="superadmin.cebu@cebucity.gov.ph"
        )
        admin = User(
            username="admin",
            password=hash_password("admin123"),
            full_name="Municipal Command Center Admin",
            role="ADMIN",
            email="admin.command@cebucity.gov.ph"
        )
        citizen_demo = User(
            username="juan_delosreyes",
            password=hash_password("citizen123"),
            full_name="Juan Delos Reyes",
            role="CITIZEN",
            email="juan.delosreyes@email.ph",
            phone_number="09171234567",
            barangay="Pardo"
        ) 
        db.add(superadmin)
        db.add(admin)
        db.add(citizen_demo)
        db.commit()
        print("[+] Seeded Superadmin (superadmin / admin123), Admin (admin / admin123), and Citizen (juan_delosreyes / citizen123) accounts.")

    if db.query(Report).count() > 0 and not force_reseed:
        return

    if force_reseed:
        db.query(NotificationLog).delete()
        db.query(Report).delete()
        db.commit()

    print("[*] Seeding database with realistic Cebu City (Mambaling & Pardo) incident reports...")

    samples = [
        {
            "ticket_number": "TUGON-CEBU-0001",
            "title": "Lagpas Tuhod na Baha sa Barangay Mambaling, Cebu City",
            "description": "Mabilis na tumaas ang baha sa Mambaling flyover at N. Bacalso Avenue dahil sa baradong drainage at malakas na buhos ng ulan. CCDRRMO emergency rescue needed.",
            "photo_filename": "flood_colon_cebu.jpg",
            "citizen_lat": 10.297780,
            "citizen_lon": 123.876180,
            "exif_lat": 10.297760,
            "exif_lon": 123.876150,
            "citizen_name": "Ramon Dela Cruz",
            "citizen_contact": "ramon.cebu@email.ph",
            "created_offset_hours": 3
        },
        {
            "ticket_number": "TUGON-CEBU-0002",
            "title": "Malaking Lubak sa N. Bacalso Ave Mambaling Delikado sa Motor",
            "description": "Napakalalaking pothole at sira ang aspalto sa N. Bacalso Avenue malapit sa Mambaling flyover sa Cebu City. DEPW engineering team response requested.",
            "photo_filename": "pothole_bacalso_cebu.jpg",
            "citizen_lat": 10.297800,
            "citizen_lon": 123.876200,
            "exif_lat": 10.297810,
            "exif_lon": 123.876220,
            "citizen_name": "Maria Santos",
            "citizen_contact": "maria.santos@email.ph",
            "created_offset_hours": 6
        },
        {
            "ticket_number": "TUGON-CEBU-0003",
            "title": "Tambak na Basura at Waste Material sa Barangay Pardo, Cebu City",
            "description": "Ilang araw nang hindi nahahakot ang mga basurang nakatambak sa bangketa ng Poblacion Pardo. DPS garbage hauling and waste clearing needed immediately.",
            "photo_filename": "waste_carbon_cebu.jpg",
            "citizen_lat": 10.289100,
            "citizen_lon": 123.862400,
            "exif_lat": 10.289120,
            "exif_lon": 123.862420,
            "citizen_name": "Juan Reyes",
            "citizen_contact": "juan.reyes@email.ph",
            "created_offset_hours": 12
        },
        {
            "ticket_number": "TUGON-CEBU-0004",
            "title": "Sunog sa mga Residential Area sa Kinalumsan Bridge Mambaling",
            "description": "May malaking residential fire malapit sa Kinalumsan River bridge sa Mambaling Cebu City. Bureau of Fire Protection (BFP) emergency response required.",
            "photo_filename": "sparking_transformer_cebu.jpg",
            "citizen_lat": 10.296500,
            "citizen_lon": 123.875500,
            "exif_lat": 10.296510,
            "exif_lon": 123.875520,
            "citizen_name": "Engr. Paul Villanueva",
            "citizen_contact": "paul.v@email.ph",
            "created_offset_hours": 1
        },
        {
            "ticket_number": "TUGON-CEBU-0005",
            "title": "Umano'y Baha sa Pardo pero Litrato ay Galing Manila (Fraud Demo)",
            "description": "Sinasabing may baha raw sa Barangay Pardo Cebu City, ngunit ang litrato ay kuha pala sa Metro Manila Taguig (mahigit 570 kilometro ang layo mula sa Cebu City).",
            "photo_filename": "recycled_photo_manila_spoof.jpg",
            "citizen_lat": 10.289100,   # Citizen reports in Pardo, Cebu City
            "citizen_lon": 123.862400,
            "exif_lat": 14.517600,      # Photo taken in Manila BGC (570 km away)
            "exif_lon": 121.050900,
            "citizen_name": "Anonymous User",
            "citizen_contact": "unverified@demo.net",
            "created_offset_hours": 18
        },
        {
            "ticket_number": "TUGON-CEBU-0006",
            "title": "Baradong Kanal at Dengue Hazard sa Barangay Pardo (City Health Dept)",
            "description": "Napakaduming kanal sa Pardo near health center na hindi umaagos ang tubig at amoy imburnal. City Health Department (CHD) inspection and dengue vector control needed.",
            "photo_filename": "no_exif_guadalupe_dengue.jpg",
            "citizen_lat": 10.289500,   # Barangay Pardo, Cebu City
            "citizen_lon": 123.863000,
            "exif_lat": None,           # Privacy mode stripped EXIF
            "exif_lon": None,
            "citizen_name": "Barangay Health Worker Elena",
            "citizen_contact": "elena.bhw@email.ph",
            "created_offset_hours": 24
        }
    ]

    for item in samples:
        # Run AI Multimodal Classifier
        ai_res = classifier.predict(item["title"], item["description"])
        
        # Run GPS / EXIF Verification against Cebu City bounds
        verif = verify_geolocation(
            exif_lat=item["exif_lat"],
            exif_lon=item["exif_lon"],
            device_lat=item["citizen_lat"],
            device_lon=item["citizen_lon"]
        )

        final_lat = verif["final_lat"] or item["citizen_lat"]
        final_lon = verif["final_lon"] or item["citizen_lon"]
        address = reverse_geocode(final_lat, final_lon)

        # Status determination
        if "FLAGGED" in verif["status"]:
            initial_status = "FLAGGED"
        elif ai_res["urgency"] == "CRITICAL":
            initial_status = "DISPATCHED"
        else:
            initial_status = "VERIFIED"

        report = Report(
            ticket_number=item["ticket_number"],
            title=item["title"],
            description=item["description"],
            category=ai_res["predicted_sector"],
            predicted_category=ai_res["predicted_sector"],
            assigned_office=ai_res.get("assigned_office"),
            confidence=ai_res["confidence"],
            urgency=ai_res["urgency"],
            multimodal_breakdown=json.dumps({
                "keywords": ai_res["matched_keywords"],
                "fused_dist": ai_res["fused_distribution"],
                "text_dist": ai_res["text_distribution"]
            }),
            status=initial_status,
            photo_filename=item["photo_filename"],
            exif_data=json.dumps({
                "has_exif": item["exif_lat"] is not None,
                "lat": item["exif_lat"],
                "lon": item["exif_lon"],
                "status": verif["status"]
            }),
            citizen_lat=item["citizen_lat"],
            citizen_lon=item["citizen_lon"],
            exif_lat=item["exif_lat"],
            exif_lon=item["exif_lon"],
            gps_distance_m=verif["distance_m"],
            verification_status=verif["status"],
            verification_notes=verif["notes"],
            address=address,
            citizen_name=item["citizen_name"],
            citizen_contact=item["citizen_contact"],
            created_at=datetime.now(timezone.utc) - timedelta(hours=item["created_offset_hours"])
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Trigger notification dispatch for initial demonstration
        if initial_status in ("DISPATCHED", "VERIFIED"):
            dispatch_sector_notification(db, report)

    print("[+] Database successfully seeded with 6 realistic Cebu City (Mambaling & Pardo) incident scenarios.")
