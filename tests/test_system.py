import unittest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import init_db, SessionLocal
from app.seeder import seed_sample_reports
from app.verifier import extract_exif_data, haversine_distance, verify_geolocation, is_within_cebu_city
from app.classifier import classifier
from app.config import UPLOAD_DIR

client = TestClient(app)

class TestTugonAI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        with SessionLocal() as db:
            seed_sample_reports(db, force_reseed=True)

    def test_cebu_city_boundary_jurisdiction(self):
        # 1. Coordinates inside Cebu City (including Mambaling and Pardo)
        self.assertTrue(is_within_cebu_city(10.3117, 123.8933))  # Fuente Osmeña Circle
        self.assertTrue(is_within_cebu_city(10.2966, 123.8998))  # Colon Street
        self.assertTrue(is_within_cebu_city(10.2978, 123.8762))  # Barangay Mambaling
        self.assertTrue(is_within_cebu_city(10.2891, 123.8624))  # Barangay Pardo
        self.assertTrue(is_within_cebu_city(10.3297, 123.9063))  # Cebu IT Park Lahug

        # 2. Coordinates outside Cebu City (Manila / Other regions)
        self.assertFalse(is_within_cebu_city(14.5176, 121.0509)) # Metro Manila
        self.assertFalse(is_within_cebu_city(7.1907, 125.4553))  # Davao City

    def test_haversine_distance(self):
        # Distance between Mambaling (10.2978, 123.8762) and Pardo (10.2891, 123.8624) ~1.78 km
        d = haversine_distance(10.2978, 123.8762, 10.2891, 123.8624)
        self.assertTrue(1200 < d < 2200, f"Expected ~1.78km, got {d}m")

        # Zero distance
        self.assertAlmostEqual(haversine_distance(10.3, 123.9, 10.3, 123.9), 0.0, places=2)

    def test_exif_extraction_genuine(self):
        sample_path = Path(UPLOAD_DIR) / "flood_colon_cebu.jpg"
        if not sample_path.exists():
            self.skipTest("Sample images not yet generated.")
        
        exif = extract_exif_data(str(sample_path))
        self.assertTrue(exif["has_exif"])
        self.assertIsNotNone(exif["lat"])
        self.assertIsNotNone(exif["lon"])
        self.assertAlmostEqual(exif["lat"], 10.296600, places=3)
        self.assertAlmostEqual(exif["lon"], 123.899800, places=3)
        self.assertEqual(exif["camera_make"], "Samsung")

    def test_exif_missing_fallback(self):
        sample_path = Path(UPLOAD_DIR) / "no_exif_guadalupe_dengue.jpg"
        if not sample_path.exists():
            self.skipTest("Sample images not yet generated.")

        exif = extract_exif_data(str(sample_path))
        self.assertIsNone(exif["lat"])
        self.assertIsNone(exif["lon"])

        # Test verification module fallback behavior in Cebu City
        verif = verify_geolocation(
            exif_lat=exif["lat"],
            exif_lon=exif["lon"],
            device_lat=10.3229,
            device_lon=123.8837
        )
        self.assertEqual(verif["status"], "EXIF_MISSING_FALLBACK_ACTIVE")
        self.assertEqual(verif["final_lat"], 10.3229)
        self.assertIn("Cebu City", verif["notes"])

    def test_gps_discrepancy_flagged(self):
        # Scenario: Photo taken in Manila BGC (14.5176, 121.0509), but citizen reported in Mambaling Cebu City (10.2978, 123.8762)
        verif = verify_geolocation(
            exif_lat=14.5176,
            exif_lon=121.0509,
            device_lat=10.2978,
            device_lon=123.8762,
            threshold_meters=200.0
        )
        self.assertEqual(verif["status"], "GPS_DISCREPANCY_FLAGGED")
        self.assertGreater(verif["distance_m"], 500000)  # > 500 km away

    def test_multimodal_classification_tagalog(self):
        # 1. Infrastructure (DEPW)
        res_dpwh = classifier.predict(
            title="Sirang Kalsada sa Mambaling Cebu City",
            description="May malalim na lubak at bitak sa gitna ng daan delikado sa motor sa Mambaling"
        )
        self.assertEqual(res_dpwh["predicted_sector"], "INFRASTRUCTURE_UTILITIES")
        self.assertEqual(res_dpwh["assigned_office"], "DEPW")
        self.assertGreater(res_dpwh["confidence"], 0.4)

        # 2. First Responders (CCDRRMO) Flood & Rescue
        res_flood = classifier.predict(
            title="Baha sa Pardo Cebu City",
            description="Mabilis tumataas ang tubig baha lagpas tuhod sa Pardo kailangan ng rescue"
        )
        self.assertEqual(res_flood["predicted_sector"], "FIRST_RESPONDERS")
        self.assertEqual(res_flood["assigned_office"], "CCDRRMO")
        self.assertEqual(res_flood["urgency"], "CRITICAL")

        # 3. Waste Management (DPS)
        res_waste = classifier.predict(
            title="Tambak na Basura sa Mambaling",
            description="Napakabahong tambak ng basura at plastic sa kanto sa Mambaling hindi nahahakot"
        )
        self.assertEqual(res_waste["predicted_sector"], "INFRASTRUCTURE_UTILITIES")
        self.assertEqual(res_waste["assigned_office"], "DPS")

        # 4. Fire / Rescue (BFP)
        res_fire = classifier.predict(
            title="Sunog sa Pardo Cebu City",
            description="May malaking sunog sa mga bahay sa Pardo kailangan ng pamatay sunog"
        )
        self.assertEqual(res_fire["predicted_sector"], "FIRST_RESPONDERS")
        self.assertEqual(res_fire["assigned_office"], "BFP")
        self.assertEqual(res_fire["urgency"], "CRITICAL")

    def test_api_analytics(self):
        res = client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_reports", data)
        self.assertIn("sector_breakdown", data)
        self.assertIn("office_breakdown", data)
        self.assertIn("verified_genuine", data)

    def test_api_reports_list(self):
        res = client.get("/api/reports")
        self.assertEqual(res.status_code, 200)
        reports = res.json()
        self.assertIsInstance(reports, list)
        self.assertGreater(len(reports), 0)

    def test_api_preview_endpoint(self):
        res = client.post("/api/analyze-preview", data={
            "title": "Baha sa Mambaling Cebu City",
            "description": "Umaapaw na ang tubig sa kalsada kailangan ng rescue CCDRRMO"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["classification"]["predicted_sector"], "FIRST_RESPONDERS")
        self.assertEqual(data["classification"]["assigned_office"], "CCDRRMO")

if __name__ == "__main__":
    unittest.main()
