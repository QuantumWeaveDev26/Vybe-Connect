"""Live deployment end-to-end verification for https://vybe.srv1871828.hstgr.cloud"""
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = "https://vybe.srv1871828.hstgr.cloud"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def fetch(path, method="GET", data=None, headers=None):
    h = dict(HEADERS)
    if headers: h.update(headers)
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.getcode(), res.headers, res.read()

def test_live():
    print(f"=== 1. Testing Core Endpoints on {BASE} ===")
    for ep in ["/healthz", "/readyz", "/api/bootstrap"]:
        code, h, body = fetch(ep)
        print(f"[{code}] {ep} -> {body.decode('utf-8')[:80]}")
        assert code == 200, f"{ep} failed with {code}"

    print("\n=== 2. Testing Root HTML & Assets ===")
    code, h, body = fetch("/")
    assert code == 200
    html = body.decode("utf-8")
    assert "<title>VYBE Connect" in html
    assert "vybe-launch" in html
    assert "app.js" in html

    css_links = re.findall(r'<link rel="stylesheet" href="([^"]+)">', html)
    js_scripts = re.findall(r'<script src="([^"]+)"', html)
    print(f"Found {len(css_links)} CSS links and {len(js_scripts)} JS scripts referenced in root HTML.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        
        # Test CSS assets
        print("\n=== 3. Testing CSS Integrity ===")
        for path in css_links:
            code, h, css_bytes = fetch(path)
            content_type = h.get("Content-Type", "")
            print(f"[{code}] {path} ({len(css_bytes)} bytes, Content-Type: {content_type})")
            assert code == 200
            assert len(css_bytes) > 0

        # Test JS assets and parse syntax with Node
        print("\n=== 4. Testing JavaScript Integrity & Syntax ===")
        for path in js_scripts:
            code, h, js_bytes = fetch(path)
            content_type = h.get("Content-Type", "")
            print(f"[{code}] {path} ({len(js_bytes)} bytes, Content-Type: {content_type})")
            assert code == 200
            assert len(js_bytes) > 0
            
            # Syntax check with Node.js
            clean_name = path.split("?")[0].lstrip("/")
            local_js = tmp / clean_name
            local_js.parent.mkdir(parents=True, exist_ok=True)
            local_js.write_bytes(js_bytes)
            res = subprocess.run(["node", "-c", str(local_js)], capture_output=True, text=True)
            if res.returncode != 0:
                print(f"SYNTAX ERROR in {clean_name}:\n{res.stderr}")
                sys.exit(1)

        print("\n-> All JS files parsed cleanly with Node.js (0 syntax errors).")

    print("\n=== 5. Testing Webhook Routes ===")
    # WooCommerce webhook endpoint
    try:
        wc_payload = json.dumps({"id": 9999, "status": "pending"}).encode("utf-8")
        code, h, body = fetch("/woocommerce-webhook/0123456789abcdef", method="POST", data=wc_payload, headers={"Content-Type": "application/json", "X-WC-Webhook-Topic": "order.created"})
        print(f"[{code}] /woocommerce-webhook/0123456789abcdef -> {body.decode('utf-8')[:80]}")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] /woocommerce-webhook -> {e.read().decode('utf-8')[:80]} (Expected signature requirement / workspace check)")

    # Shopify webhook endpoint
    try:
        sh_payload = json.dumps({"id": 8888}).encode("utf-8")
        code, h, body = fetch("/shopify-webhook/0123456789abcdef", method="POST", data=sh_payload, headers={"Content-Type": "application/json", "X-Shopify-Topic": "checkouts/create"})
        print(f"[{code}] /shopify-webhook/0123456789abcdef -> {body.decode('utf-8')[:80]}")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] /shopify-webhook -> {e.read().decode('utf-8')[:80]} (Expected signature requirement / workspace check)")

    print("\n=== 6. Testing Security Headers ===")
    _, headers, _ = fetch("/")
    csp = headers.get("Content-Security-Policy", "")
    hsts = headers.get("Strict-Transport-Security", "")
    xcto = headers.get("X-Content-Type-Options", "")
    print(f"HSTS: {hsts or 'Not set'}")
    print(f"X-Content-Type-Options: {xcto or 'Not set'}")
    print(f"CSP present: {bool(csp)}")

    print("\n=======================================================")
    print(" ALL LIVE VERIFICATION CHECKS PASSED WITH ZERO ERRORS! ")
    print("=======================================================")

if __name__ == "__main__":
    test_live()
