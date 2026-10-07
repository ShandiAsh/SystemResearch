# TUGON AI: Intelligent Municipal Incident Reporting & Verification System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Pillow EXIF](https://img.shields.io/badge/Forensics-Pillow%20EXIF-orange.svg)](https://python-pillow.org/)
[![CSS Design](https://img.shields.io/badge/UI-Bespoke%20CSS-blueviolet.svg)](static/css/styles.css)

> **Capstone Project System**: An AI-assisted web and mobile application for **Barangay Mambaling** and **Barangay Pardo**, Cebu City, that verifies citizen reports through photo metadata/GPS, classifies incident text and images via the **ReAct Framework**, advises citizens on pre-requisite document requirements, and automatically routes reports to the proper partner government office under the **Adaptive Oversight Calibration Model (AOCM)** human-in-the-loop design.

---

## 📌 1. Theoretical & Conceptual Frameworks

### A. Adaptive Oversight Calibration Model (AOCM) (Vance et al., 2025)
AOCM dictates that as artificial intelligence transitions into decision-making, systems must maintain a strict balance between automation and human veto power. TUGON AI automates **80% of tedious cognitive triage** (parse text, analyze vision cues, extract EXIF GPS, check fraud), while leaving final execution privileges in the human supervisor's / citizen's hands (citizen-in-the-loop veto power).

### B. ReAct (Reasoning and Acting) Cognitive Architecture (Yao et al., 2022)
TUGON AI's classification engine interleave dynamic reasoning ("thinking") with external tool actions ("acting"):
1. **Thought 1**: Parse citizen narrative (Tagalog/Bisaya NLP) & incident details.
2. **Action 1**: Extract photo EXIF metadata & execute Haversine distance geofencing against Cebu City bounds.
3. **Observation 1**: Evaluate location fraud status and calculate distance delta.
4. **Thought 2**: Perform multimodal late fusion to determine primary sector category and 11-office target.
5. **Action 2**: Generate automated requirements advisory checklist tailored to the assigned office.
6. **Final Reasoning (AOCM)**: Assign priority, log 80% automated triage, and await citizen consent for email dispatch.

### C. Alignment with Global & Technical Standards
- **SDG 11 (Targets 11.5 & 11.b)**: Resilient cities and technology-supported disaster risk reduction.
- **ISO 25010 Quality Model**: Evaluated for Functionality, Usability, Reliability, Performance Efficiency, and Security.

---

## 🏛️ 2. Supported Government Sectors & 11 Partner Offices (Cebu City Scope)

```
TUGON AI Classification & Dispatch Engine (Barangay Mambaling & Barangay Pardo, Cebu City)
├── 🚑 1. First Responders and Emergency Rescue (FIRST_RESPONDERS)
│   ├── CCDRRMO — Cebu City Disaster Risk Reduction and Management Office
│   ├── BFP — Bureau of Fire Protection – Cebu City
│   └── CCTO — Cebu City Transportation Office
├── 🤝 2. Relief, Food, and Social Welfare (SOCIAL_WELFARE)
│   ├── DSWD — Department of Social Welfare and Services (DSWS / DSWD)
│   └── NUTRITION — Cebu City Nutrition Office
├── 🏥 3. Medical Care and Public Health (PUBLIC_HEALTH)
│   ├── CHD — City Health Department
│   └── CCMC — Cebu City Medical Center
├── 🏗️ 4. Infrastructure Clearing and Utilities Restoration (INFRASTRUCTURE_UTILITIES)
│   ├── DEPW — Department of Engineering and Public Works
│   └── DPS — Department of Public Services
└── 🌾 5. Farming, Animal, and Rural Aid (AGRICULTURE_ANIMAL)
    ├── CAD — City Agriculture Department
    └── DVMF — Department of Veterinary Medicine and Fisheries
```

---

## 🔬 3. System Architecture & Core Modules

```
+-----------------------------------------------------------------------------------+
|               CITIZEN REPORTING PORTAL (Barangays Mambaling & Pardo)              |
|  - Native Mobile Camera Capture (capture="environment") / Gallery Upload         |
|  - Device Geolocation Locking (navigator.geolocation)                             |
|  - Real-Time Vernacular NLP Feedback (Tagalog / Bisaya / English)                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        FASTAPI UNIFIED INFERENCE & ROUTER                         |
+--------------------+------------------------------------+-------------------------+
                     |                                    |
                     v                                    v
+------------------------------------+   +------------------------------------+
|   MULTIMODAL CLASSIFICATION ENGINE |   |     EXIF / GPS FORENSIC VERIFIER   |
| - ReAct Cognitive Loop Engine      |   | - Pillow GPSInfo Tag Extractor     |
| - Visual Texture & Spectral Vision |   | - Haversine Distance Delta Check   |
| - Requirements Advisory Generator  |   | - Mambaling/Pardo Geofence Check   |
+--------------------+---------------+   +----------------+-------------------+
                     |                                    |
                     +-----------------+------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                           AOCM DECISION & TRIAGE ENGINE                           |
| - Priority Scoring: CRITICAL, HIGH, MEDIUM, LOW                                   |
| - Forensic Flags: VERIFIED_GENUINE, GPS_DISCREPANCY_FLAGGED, FALLBACK_ACTIVE      |
| - 80% Automated Triage + Citizen-in-the-Loop Veto Power                           |
+--------------------+------------------------------------+-------------------------+
                     |                                    |
                     v                                    v
+------------------------------------+   +------------------------------------+
|       SQLITE / POSTGRESQL DB       |   |    AUTOMATED SECTOR DISPATCHER     |
| - Incident Audit Trails            |   | - HTML Emergency Dispatch Mails    |
| - ReAct Traces & Requirements      |   | - Auto-alerting 11 Partner Offices |
+--------------------+---------------+   +----------------+-------------------+
                     |                                    |
                     +-----------------+------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                   COMMAND CENTER & SECTOR DASHBOARDS (Leaflet Map)                |
+-----------------------------------------------------------------------------------+
```

---

## 📊 4. Comparative Matrix (Literature Review)

| Feature | TUGON AI | MapaKalamidad.ph | Ushahidi | DSWD OpenG2P | ELYA |
|---|---|---|---|---|---|
| **Multimodal (text + image) classification** | **Yes** | Partial | No | No | No |
| **GPS / EXIF-based automated verification** | **Yes** | Partial | Partial | No | No |
| **Suggests specific government office (11 Offices)** | **Yes** | No | No | No | Partial |
| **Provides requirements/document checklist** | **Yes** | No | No | No | No |
| **Opt-in automated notification to sector** | **Yes** | No | No | No | No |
| **Citizen-controlled human-in-the-loop step (AOCM)** | **Yes** | No | Partial | No | Yes |
| **Government-side dashboard, no account needed** | **Yes** | Partial | No | No | No |

---

##  5. How to Run the Project

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: (Optional) Re-seed Database with Mambaling & Pardo Demo Reports
```bash
python -c "from app.database import engine, init_db, Base, SessionLocal; from app.seeder import seed_sample_reports; Base.metadata.drop_all(bind=engine); init_db(); db=SessionLocal(); seed_sample_reports(db, force_reseed=True); db.close()"
```

### Step 3: Launch the TUGON AI Server
```bash
python main.py
```

### Step 4: Open in Your Browser
- **Citizen Portal**: [http://localhost:8000](http://localhost:8000)
- **Sector Command Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **FastAPI Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 6. Running Automated Unit Tests

Run the complete test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

All 9 unit tests pass cleanly.
