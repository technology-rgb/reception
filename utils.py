import re
import socket
import subprocess
import threading
from io import BytesIO
import qrcode


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def start_public_tunnel(port: int = 8501) -> str | None:
    """
    Opens a free public HTTPS tunnel via localhost.run using the SSH client
    built into Windows 10/11. No account, no install, no extra terminal.
    Returns the public URL or None if SSH / the tunnel service is unavailable.
    """
    try:
        proc = subprocess.Popen(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-o", "LogLevel=ERROR",
                "-R", f"80:localhost:{port}",
                "localhost.run",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        result = [None]
        ready = threading.Event()

        def _reader():
            for line in proc.stdout:
                m = re.search(r"https://[a-z0-9\-]+\.lhr\.life", line)
                if m:
                    result[0] = m.group(0).rstrip("/")
                    ready.set()
                    # Keep draining so the SSH process stays alive
                    for _ in proc.stdout:
                        pass
                    return
            ready.set()  # SSH exited without giving a URL

        threading.Thread(target=_reader, daemon=True).start()
        ready.wait(timeout=15)
        return result[0]
    except Exception:
        return None


def make_qr_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
