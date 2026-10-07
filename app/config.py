import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "images" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/tugon_ai.db")

# Target Jurisdiction: Cebu City, Philippines
TARGET_MUNICIPALITY = "Cebu City, Philippines"
CEBU_CITY_CENTER = (10.3117, 123.8933)  # Fuente Osmeña Circle, Cebu City
CEBU_CITY_BOUNDS = {
    "min_lat": 10.2400,
    "max_lat": 10.4500,
    "min_lon": 123.7500,
    "max_lon": 123.9600
}

# GPS & Geofencing Verification
MAX_GPS_DISTANCE_METERS = float(os.getenv("MAX_GPS_DISTANCE_METERS", "200.0"))

# Email / Notification Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "tugon.cebu.alerts@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SIMULATE_EMAIL = os.getenv("SIMULATE_EMAIL", "true").lower() == "true"

# =========================================================================
# 5 Government Sector Categories (Scope and Delimitation)
# =========================================================================
SECTOR_CATEGORIES = {
    "FIRST_RESPONDERS": {
        "name": "First Responders and Emergency Rescue",
        "description": "Emergency search and rescue, structural fires, and critical road traffic incident management",
        "color": "#ef4444",  # Red
        "icon": "fa-truck-medical",
        "offices": ["CCDRRMO", "BFP", "CCTO"]
    },
    "SOCIAL_WELFARE": {
        "name": "Relief, Food, and Social Welfare",
        "description": "Evacuee relief aid, calamity assistance, displaced family support, and community nutrition",
        "color": "#f59e0b",  # Amber
        "icon": "fa-hand-holding-heart",
        "offices": ["DSWD", "NUTRITION"]
    },
    "PUBLIC_HEALTH": {
        "name": "Medical Care and Public Health",
        "description": "Disease outbreak containment, medical emergencies, community sanitation, and hospital trauma care",
        "color": "#06b6d4",  # Cyan
        "icon": "fa-hospital",
        "offices": ["CHD", "CCMC"]
    },
    "INFRASTRUCTURE_UTILITIES": {
        "name": "Infrastructure Clearing and Utilities Restoration",
        "description": "Road and bridge structural repairs, excavation hazard safety, uncollected garbage, and post-calamity debris clearing",
        "color": "#10b981",  # Emerald
        "icon": "fa-trowel-bricks",
        "offices": ["DEPW", "DPS"]
    },
    "AGRICULTURE_ANIMAL": {
        "name": "Farming, Animal, and Rural Aid",
        "description": "Rural farming and irrigation support, crop pest control, animal rabies mitigation, veterinary welfare, and fisheries protection",
        "color": "#8b5cf6",  # Purple
        "icon": "fa-cow",
        "offices": ["CAD", "DVMF"]
    }
}

# =========================================================================
# 11 Specific Partner Government Offices in Cebu City
# =========================================================================
PARTNER_OFFICES = {
    # 1. First Responders and Emergency Rescue
    "CCDRRMO": {
        "name": "Cebu City Disaster Risk Reduction and Management Office (CCDRRMO)",
        "short_name": "CCDRRMO",
        "category": "FIRST_RESPONDERS",
        "email": "ccdrrmo.rescue@cebucity.gov.ph.mock",
        "description": "Flooding, landslides, typhoon damage, fallen trees, and search & rescue operations",
        "color": "#ef4444",
        "icon": "fa-water"
    },
    "BFP": {
        "name": "Bureau of Fire Protection – Cebu City",
        "short_name": "BFP - Cebu City",
        "category": "FIRST_RESPONDERS",
        "email": "bfp.cebucity.station@gov.ph.mock",
        "description": "Residential, commercial, and vehicular fires, chemical spills, and fire safety hazards",
        "color": "#dc2626",
        "icon": "fa-fire-extinguisher"
    },
    "CCTO": {
        "name": "Cebu City Transportation Office (CCTO)",
        "short_name": "CCTO",
        "category": "FIRST_RESPONDERS",
        "email": "ccto.traffic.ops@cebucity.gov.ph.mock",
        "description": "Vehicular collisions, traffic signal breakdowns, illegal parking, and severe road blockages",
        "color": "#ea580c",
        "icon": "fa-car-burst"
    },

    # 2. Relief, Food, and Social Welfare
    "DSWD": {
        "name": "Department of Social Welfare and Services (DSWS / DSWD)",
        "short_name": "DSWS / DSWD",
        "category": "SOCIAL_WELFARE",
        "email": "dswd.cebucity.relief@gov.ph.mock",
        "description": "Relief goods distribution, emergency shelter assistance, and support for displaced families",
        "color": "#f59e0b",
        "icon": "fa-box-open"
    },
    "NUTRITION": {
        "name": "Cebu City Nutrition Office",
        "short_name": "Nutrition Office",
        "category": "SOCIAL_WELFARE",
        "email": "nutrition.office@cebucity.gov.ph.mock",
        "description": "Emergency supplemental feeding, child malnutrition interventions, and infant food relief",
        "color": "#d97706",
        "icon": "fa-utensils"
    },

    # 3. Medical Care and Public Health
    "CHD": {
        "name": "City Health Department (CHD)",
        "short_name": "City Health Dept",
        "category": "PUBLIC_HEALTH",
        "email": "chd.sanitation@cebucity.gov.ph.mock",
        "description": "Dengue vector mitigation, stagnant water inspections, infectious outbreak monitoring, and health center triage",
        "color": "#06b6d4",
        "icon": "fa-heart-pulse"
    },
    "CCMC": {
        "name": "Cebu City Medical Center (CCMC)",
        "short_name": "CCMC Hospital",
        "category": "PUBLIC_HEALTH",
        "email": "ccmc.emergency.intake@cebucity.gov.ph.mock",
        "description": "Emergency room admissions, urgent ambulance response, trauma care, and inpatient hospital care",
        "color": "#0891b2",
        "icon": "fa-truck-medical"
    },

    # 4. Infrastructure Clearing and Utilities Restoration
    "DEPW": {
        "name": "Department of Engineering and Public Works (DEPW)",
        "short_name": "DEPW",
        "category": "INFRASTRUCTURE_UTILITIES",
        "email": "depw.engineering@cebucity.gov.ph.mock",
        "description": "Potholes, road cracks, bridge defects, drainage engineering excavations, and public infrastructure rehabilitation",
        "color": "#10b981",
        "icon": "fa-road-barrier"
    },
    "DPS": {
        "name": "Department of Public Services (DPS)",
        "short_name": "DPS",
        "category": "INFRASTRUCTURE_UTILITIES",
        "email": "dps.wasteclearing@cebucity.gov.ph.mock",
        "description": "Solid waste hauling, uncollected street garbage piles, market clearing, and clogged drainage cleaning",
        "color": "#059669",
        "icon": "fa-recycle"
    },

    # 5. Farming, Animal, and Rural Aid
    "CAD": {
        "name": "City Agriculture Department (CAD)",
        "short_name": "City Agriculture",
        "category": "AGRICULTURE_ANIMAL",
        "email": "agriculture.department@cebucity.gov.ph.mock",
        "description": "Mountain barangay crop assistance, farming irrigation, drought aid, and agricultural pest management",
        "color": "#8b5cf6",
        "icon": "fa-wheat-awn"
    },
    "DVMF": {
        "name": "Department of Veterinary Medicine and Fisheries (DVMF)",
        "short_name": "DVMF",
        "category": "AGRICULTURE_ANIMAL",
        "email": "dvmf.animalwelfare@cebucity.gov.ph.mock",
        "description": "Stray animal management, rabies prevention, livestock diseases, animal carcass disposal, and fisheries protection",
        "color": "#7c3aed",
        "icon": "fa-shield-dog"
    }
}

# Alias SECTORS to SECTOR_CATEGORIES for standard compatibility
SECTORS = SECTOR_CATEGORIES
