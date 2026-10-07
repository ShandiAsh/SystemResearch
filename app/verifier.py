import math
import logging
from typing import Dict, Any, Tuple, Optional
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from app.config import MAX_GPS_DISTANCE_METERS, CEBU_CITY_BOUNDS, CEBU_CITY_CENTER

logger = logging.getLogger("tugon.verifier")

def _convert_to_degrees(value) -> float:
    """
    Helper function to convert the GPS coordinates stored in the EXIF to degrees in float format.
    Handles tuples/rationals from Pillow (degrees, minutes, seconds).
    """
    try:
        def to_float(val):
            if hasattr(val, "numerator") and hasattr(val, "denominator"):
                return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
            if isinstance(val, tuple) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
            return float(val)

        d = to_float(value[0])
        m = to_float(value[1])
        s = to_float(value[2])

        return d + (m / 60.0) + (s / 3600.0)
    except Exception as e:
        logger.warning(f"Error converting GPS coordinates: {e}")
        return 0.0


def extract_exif_data(image_path: str) -> Dict[str, Any]:
    """
    Extracts camera metadata and GPS coordinates from an image file.
    Returns clean dictionary with lat, lon, camera info, and timestamp.
    """
    result: Dict[str, Any] = {
        "has_exif": False,
        "lat": None,
        "lon": None,
        "camera_make": None,
        "camera_model": None,
        "datetime_original": None,
        "software": None,
        "raw_tags": {}
    }

    try:
        with Image.open(image_path) as img:
            exif_raw = img.getexif()
            if not exif_raw:
                # Try fallback to _getexif() for JPEG
                if hasattr(img, "_getexif"):
                    raw_dict = img._getexif()
                    if raw_dict:
                        exif_raw = raw_dict

            if not exif_raw:
                return result

            result["has_exif"] = True
            gps_info = {}

            # Parse primary EXIF tags
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "Make":
                    result["camera_make"] = str(value).strip()
                elif tag_name == "Model":
                    result["camera_model"] = str(value).strip()
                elif tag_name in ("DateTimeOriginal", "DateTime"):
                    result["datetime_original"] = str(value).strip()
                elif tag_name == "Software":
                    result["software"] = str(value).strip()
                elif tag_name == "GPSInfo" or tag_id == 34853:
                    if isinstance(value, dict):
                        gps_info = value

            # Pillow 10+ IFD support for GPS
            if not gps_info and hasattr(exif_raw, "get_ifd"):
                try:
                    gps_ifd = exif_raw.get_ifd(0x8825)
                    if gps_ifd:
                        gps_info = gps_ifd
                except Exception:
                    pass

            # Extract GPS Latitude & Longitude if present
            if gps_info:
                parsed_gps = {}
                for key, val in gps_info.items():
                    sub_tag = GPSTAGS.get(key, key)
                    parsed_gps[sub_tag] = val

                lat_raw = parsed_gps.get("GPSLatitude")
                lat_ref = parsed_gps.get("GPSLatitudeRef")
                lon_raw = parsed_gps.get("GPSLongitude")
                lon_ref = parsed_gps.get("GPSLongitudeRef")

                if lat_raw and lon_raw:
                    lat = _convert_to_degrees(lat_raw)
                    lon = _convert_to_degrees(lon_raw)

                    if lat_ref and str(lat_ref).upper() == "S":
                        lat = -lat
                    if lon_ref and str(lon_ref).upper() == "W":
                        lon = -lon

                    if lat != 0.0 or lon != 0.0:
                        result["lat"] = round(lat, 6)
                        result["lon"] = round(lon, 6)

    except Exception as e:
        logger.error(f"Failed to read EXIF from {image_path}: {e}")

    return result


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    """
    R = 6371000.0  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def is_within_cebu_city(lat: Optional[float], lon: Optional[float]) -> bool:
    """Checks if given coordinates fall inside Cebu City municipal boundaries."""
    if lat is None or lon is None:
        return False
    return (
        CEBU_CITY_BOUNDS["min_lat"] <= lat <= CEBU_CITY_BOUNDS["max_lat"] and
        CEBU_CITY_BOUNDS["min_lon"] <= lon <= CEBU_CITY_BOUNDS["max_lon"]
    )


def verify_geolocation(
    exif_lat: Optional[float],
    exif_lon: Optional[float],
    device_lat: Optional[float],
    device_lon: Optional[float],
    threshold_meters: float = MAX_GPS_DISTANCE_METERS
) -> Dict[str, Any]:
    """
    Cross-checks the photo's embedded EXIF GPS against the citizen's browser/device live GPS.
    Enforces Cebu City municipal jurisdiction checks.
    """
    has_exif_gps = (exif_lat is not None and exif_lon is not None)
    has_device_gps = (device_lat is not None and device_lon is not None)

    verif_res = {}

    if has_exif_gps and has_device_gps:
        dist = haversine_distance(exif_lat, exif_lon, device_lat, device_lon)
        if dist <= threshold_meters:
            verif_res = {
                "status": "VERIFIED_GENUINE",
                "distance_m": dist,
                "notes": f"Verified Genuine: Photo EXIF GPS matches device location in Cebu City (Distance delta: {dist:.1f}m <= {threshold_meters}m).",
                "final_lat": exif_lat,
                "final_lon": exif_lon,
                "confidence_impact": 1.0
            }
        else:
            verif_res = {
                "status": "GPS_DISCREPANCY_FLAGGED",
                "distance_m": dist,
                "notes": f"Suspicious Discrepancy Flagged: Photo coordinates are {dist:.1f}m away from device submission location (Exceeds {threshold_meters}m threshold). Potential recycled/remote photo.",
                "final_lat": device_lat,
                "final_lon": device_lon,
                "confidence_impact": 0.6
            }

    elif has_device_gps and not has_exif_gps:
        verif_res = {
            "status": "EXIF_MISSING_FALLBACK_ACTIVE",
            "distance_m": None,
            "notes": "Fallback Active: Photo EXIF GPS was not found (iOS/privacy mode). Using device GPS in Cebu City as verified location.",
            "final_lat": device_lat,
            "final_lon": device_lon,
            "confidence_impact": 0.85
        }

    elif has_exif_gps and not has_device_gps:
        verif_res = {
            "status": "EXIF_SOLO_ACCEPTED",
            "distance_m": None,
            "notes": "Device geolocation was not permitted; extracted GPS directly from photo EXIF metadata.",
            "final_lat": exif_lat,
            "final_lon": exif_lon,
            "confidence_impact": 0.9
        }

    else:
        verif_res = {
            "status": "UNVERIFIABLE",
            "distance_m": None,
            "notes": "Unverifiable Location: Neither photo EXIF GPS nor device geolocation were provided.",
            "final_lat": None,
            "final_lon": None,
            "confidence_impact": 0.4
        }

    # Verify if within Cebu City jurisdiction
    final_lat = verif_res.get("final_lat")
    final_lon = verif_res.get("final_lon")
    if final_lat is not None and final_lon is not None:
        if not is_within_cebu_city(final_lat, final_lon):
            verif_res["notes"] += " [ALERT: Detected coordinates are OUTSIDE Cebu City boundary. TUGON AI is strictly dedicated to Cebu City.]"
            if verif_res["status"] == "VERIFIED_GENUINE":
                verif_res["status"] = "OUTSIDE_CEBU_CITY_FLAGGED"
            verif_res["confidence_impact"] *= 0.5
        else:
            verif_res["notes"] += " [Confirmed inside Cebu City Municipal Boundary.]"

    return verif_res


def reverse_geocode(lat: Optional[float], lon: Optional[float]) -> str:
    """
    Infers address from coordinates using Cebu City landmark anchors and bounds.
    """
    if lat is None or lon is None:
        return "Location Undetermined"

    # Known Cebu City coordinate anchors for instant offline reverse geocoding
    anchors = [
        (10.2966, 123.8998, "Colon Street, Downtown Cebu City"),
        (10.3117, 123.8933, "Fuente Osmeña Circle, Uptown Cebu City"),
        (10.3297, 123.9063, "Cebu IT Park, Barangay Lahug, Cebu City"),
        (10.3173, 123.9058, "Ayala Center Cebu / Cebu Business Park, Mabolo, Cebu City"),
        (10.2917, 123.8986, "Carbon Market / Ermita, Cebu City"),
        (10.3117, 123.9181, "SM City Cebu, North Reclamation Area, Mabolo, Cebu City"),
        (10.2818, 123.8821, "South Road Properties (SRP) / SM Seaside, Cebu City"),
        (10.2978, 123.8762, "N. Bacalso Avenue, Barangay Mambaling, Cebu City"),
        (10.3541, 123.9133, "Gov. Cuenco Ave, Barangay Banilad / Talamban, Cebu City"),
        (10.3229, 123.8837, "Guadalupe Riverbanks, Barangay Guadalupe, Cebu City"),
        (10.3134, 123.8980, "General Maxilom Ave (Mango Ave), Cebu City"),
        (10.2933, 123.9014, "Cebu City Hall / Plaza Sugbo, Downtown Cebu City"),
        (10.2891, 123.8624, "Barangay Pardo / Basak San Nicolas, Cebu City"),
        (10.3667, 123.8667, "Transcentral Highway, Barangay Busay, Cebu City"),
    ]

    best_address = None
    min_dist = float("inf")

    for a_lat, a_lon, addr in anchors:
        d = haversine_distance(lat, lon, a_lat, a_lon)
        if d < min_dist:
            min_dist = d
            best_address = addr

    if min_dist < 2500:  # Within 2.5 km of anchor
        return f"Near {best_address} (Lat: {lat:.4f}, Lon: {lon:.4f})"

    if is_within_cebu_city(lat, lon):
        return f"Cebu City Geographic Pin ({lat:.5f}° N, {lon:.5f}° E)"

    return f"Outside Cebu City Boundary ({lat:.5f}° N, {lon:.5f}° E)"

