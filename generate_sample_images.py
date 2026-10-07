import os
from pathlib import Path
from PIL import Image, ImageDraw
from app.config import UPLOAD_DIR

def decimal_to_dms(deg_float):
    deg = int(deg_float)
    min_float = (deg_float - deg) * 60.0
    minute = int(min_float)
    sec = round((min_float - minute) * 60.0, 2)
    return (float(deg), float(minute), float(sec))

def create_sample_image(
    filename: str,
    title: str,
    subtitle: str,
    bg_color: tuple,
    lat: float = None,
    lon: float = None,
    camera_make: str = "Apple",
    camera_model: str = "iPhone 15 Pro"
):
    path = Path(UPLOAD_DIR) / filename
    
    # Create canvas
    img = Image.new("RGB", (640, 480), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Inner border
    draw.rectangle([10, 10, 630, 470], outline=(255, 255, 255, 120), width=3)

    # Draw header bar
    draw.rectangle([10, 10, 630, 90], fill=(15, 23, 42))
    draw.text((25, 20), "TUGON AI - CEBU CITY INCIDENT EVIDENCE", fill=(56, 189, 248))
    draw.text((25, 45), title.upper(), fill=(255, 255, 255))
    draw.text((25, 68), "JURISDICTION: CEBU CITY, PHILIPPINES", fill=(148, 163, 184))

    # Add forensic simulation watermark
    draw.rectangle([20, 360, 620, 460], fill=(15, 23, 42, 200))
    draw.text((30, 370), f"CAMERA: {camera_make} {camera_model}", fill=(203, 213, 225))
    if lat and lon:
        draw.text((30, 395), f"EXIF GPS: {lat:.6f}° N, {lon:.6f}° E", fill=(74, 222, 128))
    else:
        draw.text((30, 395), "EXIF GPS: [STRIPPED / PRIVACY MODE]", fill=(248, 113, 113))
    draw.text((30, 420), f"CEBU LOCATION: {subtitle}", fill=(148, 163, 184))

    # Add EXIF if coordinates provided
    exif = img.getexif()
    exif[271] = camera_make
    exif[272] = camera_model
    exif[306] = "2026:09:07 14:22:10"

    if lat is not None and lon is not None:
        gps_ifd = exif.get_ifd(0x8825)
        gps_ifd[1] = "N" if lat >= 0 else "S"
        gps_ifd[2] = decimal_to_dms(abs(lat))
        gps_ifd[3] = "E" if lon >= 0 else "W"
        gps_ifd[4] = decimal_to_dms(abs(lon))
        exif[0x8825] = gps_ifd

    img.save(path, format="JPEG", exif=exif)
    print(f"[+] Generated Cebu sample image: {path.name} (GPS: {lat}, {lon})")

def main():
    print("Generating demo images with Cebu City EXIF GPS metadata...")
    # 1. Flood in Colon Street, Cebu City
    create_sample_image(
        "flood_colon_cebu.jpg",
        "Severe Flash Flood / Baha sa Colon",
        "Colon Street, Downtown Cebu City - Knee Deep Water",
        (56, 110, 150),  # Blue/water tone
        lat=10.296600,
        lon=123.899800,
        camera_make="Samsung",
        camera_model="Galaxy S23 Ultra"
    )

    # 2. Pothole in N. Bacalso Ave, Cebu City
    create_sample_image(
        "pothole_bacalso_cebu.jpg",
        "Deep Pothole / Lubak sa N. Bacalso",
        "N. Bacalso Ave, Mambaling, Cebu City",
        (80, 80, 85),  # Asphalt gray
        lat=10.297800,
        lon=123.876200,
        camera_make="Apple",
        camera_model="iPhone 14"
    )

    # 3. Uncollected Waste in Carbon Market, Cebu City
    create_sample_image(
        "waste_carbon_cebu.jpg",
        "Illegal Waste Dumpsite / Tambak sa Carbon",
        "Carbon Market, Ermita, Cebu City",
        (110, 95, 75),  # Earthy waste tone
        lat=10.291700,
        lon=123.898600,
        camera_make="Xiaomi",
        camera_model="Redmi Note 12"
    )

    # 4. Sparking Transformer in Cebu IT Park, Lahug
    create_sample_image(
        "sparking_transformer_cebu.jpg",
        "Sparking Transformer & Live Wire",
        "Cebu IT Park, Barangay Lahug, Cebu City",
        (180, 80, 40),  # Electrical spark tone
        lat=10.329700,
        lon=123.906300,
        camera_make="Google",
        camera_model="Pixel 8 Pro"
    )

    # 5. Remote Spoofed Photo (Taken in Manila BGC, submitted as Fuente Osmeña Cebu)
    create_sample_image(
        "recycled_photo_manila_spoof.jpg",
        "Remote / Spoofed Photo (From Manila)",
        "Captured in Manila (14.5176 N) - Spoofed in Cebu City",
        (70, 75, 80),
        lat=14.517600,
        lon=121.050900,
        camera_make="Sony",
        camera_model="Alpha A7 IV"
    )

    # 6. Privacy Stripped Photo in Barangay Guadalupe, Cebu City (No EXIF GPS)
    create_sample_image(
        "no_exif_guadalupe_dengue.jpg",
        "Stagnant Drainage Water / Dengue Hazard",
        "Barangay Guadalupe, Cebu City - EXIF GPS Stripped",
        (60, 90, 70),  # Algae green
        lat=None,
        lon=None,
        camera_make="Apple",
        camera_model="iPhone 15"
    )

    # Also maintain legacy names as copies for backward compatibility
    for old_name, new_name in [
        ("flood_marikina.jpg", "flood_colon_cebu.jpg"),
        ("pothole_commonwealth.jpg", "pothole_bacalso_cebu.jpg"),
        ("waste_tondo.jpg", "waste_carbon_cebu.jpg"),
        ("sparking_transformer.jpg", "sparking_transformer_cebu.jpg"),
        ("recycled_photo_bgc.jpg", "recycled_photo_manila_spoof.jpg"),
        ("no_exif_dengue.jpg", "no_exif_guadalupe_dengue.jpg")
    ]:
        src = Path(UPLOAD_DIR) / new_name
        dst = Path(UPLOAD_DIR) / old_name
        if src.exists():
            import shutil
            shutil.copyfile(src, dst)

    print("All Cebu City sample images generated successfully.")

if __name__ == "__main__":
    main()
