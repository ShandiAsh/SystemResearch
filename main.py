import socket
import uvicorn

def get_local_ip() -> str:
    """Detect the local machine IP address on the Wi-Fi/LAN network for mobile access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print("==========================================================")
    print("  TUGON AI - Intelligent Municipal Incident Platform")
    print("  Multimodal Classification | EXIF/GPS Forensic Verification")
    print("----------------------------------------------------------")
    print(f"  [Desktop Web]:      http://localhost:{port}")
    print(f"  [Mobile on Wi-Fi]:  http://{local_ip}:{port}")
    print(f"  [Command Center]:   http://localhost:{port}/dashboard")
    print(f"  [Mobile Dashboard]: http://{local_ip}:{port}/dashboard")
    print(f"  [REST API Docs]:    http://localhost:{port}/docs")
    print("----------------------------------------------------------")
    print("  NOTE: Do NOT type '0.0.0.0' in your browser.")
    print(f"  Use http://localhost:{port} on PC or http://{local_ip}:{port} on phone.")
    print("==========================================================")

    # Binding to 0.0.0.0 allows phones and other devices on the same Wi-Fi network to access
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
