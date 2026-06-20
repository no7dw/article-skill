#!/usr/bin/env python3
"""
Take a screenshot of a URL through Chrome DevTools Protocol.

Usage:
    python scripts/chrome_screenshot.py <url> <output_path> [cdp_port]
"""

import base64
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import websocket as ws_client

CDP_DEFAULT_PORT = 9222
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]


def find_free_port(start=9222):
    for port in range(start, start + 100):
        try:
            sock = socket.socket()
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError("Could not find a free Chrome CDP port")


def is_chrome_listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def start_chrome(cdp_port=None):
    if cdp_port is None:
        cdp_port = find_free_port()

    for check_port in range(cdp_port, cdp_port + 20):
        if is_chrome_listening(check_port):
            return check_port

    chrome_path = next((path for path in CHROME_PATHS if os.path.exists(path)), None)
    if not chrome_path:
        raise RuntimeError("Chrome or Chromium was not found")

    user_data_dir = f"/tmp/chrome-screenshot-{os.getuid()}"
    os.makedirs(user_data_dir, exist_ok=True)

    proc = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={cdp_port}",
            f"--user-data-dir={user_data_dir}",
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        if is_chrome_listening(cdp_port):
            return cdp_port
        time.sleep(0.3)
        if proc.poll() is not None:
            raise RuntimeError(f"Chrome exited unexpectedly with code {proc.returncode}")

    raise RuntimeError("Chrome did not start in time")


def get_json(url, data=None, method=None):
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def cdp_ws_send(ws, message_id, method, params=None):
    payload = json.dumps({"id": message_id, "method": method, "params": params or {}})
    ws.send(payload)
    while True:
        data = json.loads(ws.recv())
        if data.get("id") == message_id:
            return data


def get_or_create_tab(port, url):
    targets = get_json(f"http://127.0.0.1:{port}/json")
    for target in targets:
        if target.get("url") == url:
            return target["id"], target["webSocketDebuggerUrl"]

    created = get_json(f"http://127.0.0.1:{port}/json/new", method="POST")
    return created["id"], created["webSocketDebuggerUrl"]


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/chrome_screenshot.py <url> <output_path> [cdp_port]")
        sys.exit(1)

    url = sys.argv[1]
    output_path = sys.argv[2]
    cdp_port = int(sys.argv[3]) if len(sys.argv) > 3 else CDP_DEFAULT_PORT

    chrome_port = cdp_port
    chrome_started_by_us = False
    if not is_chrome_listening(chrome_port):
        print(f"[chrome_screenshot] No Chrome on port {chrome_port}, launching...", file=sys.stderr)
        chrome_port = start_chrome(cdp_port)
        chrome_started_by_us = True
        print(f"[chrome_screenshot] Chrome started on port {chrome_port}", file=sys.stderr)

    try:
        tab_id, ws_url = get_or_create_tab(chrome_port, url)
        print(f"[chrome_screenshot] Using tab {tab_id}", file=sys.stderr)

        ws = ws_client.create_connection(ws_url, suppress_origin=True)
        ws.settimeout(30)

        cdp_ws_send(ws, 1, "Page.navigate", {"url": url})
        print(f"[chrome_screenshot] Navigating to {url}", file=sys.stderr)
        time.sleep(3)

        response = cdp_ws_send(
            ws,
            2,
            "Page.captureScreenshot",
            {"format": "png", "captureBeyondViewport": True},
        )
        image_data = response.get("result", {}).get("data")
        if not image_data:
            raise RuntimeError(f"Screenshot failed: {response}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as handle:
            handle.write(base64.b64decode(image_data))
        print(f"[chrome_screenshot] Saved to {output_path}", file=sys.stderr)

        ws.close()
    finally:
        if chrome_started_by_us:
            subprocess.run(
                ["pkill", "-f", f"--remote-debugging-port={chrome_port}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


if __name__ == "__main__":
    def cleanup(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        import websocket  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])

    main()
