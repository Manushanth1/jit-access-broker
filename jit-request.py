#!/usr/bin/env python3
"""
JIT Access Broker - CLI Client
Usage: python jit-request.py --reason "fix nginx crash" --minutes 15
"""
import argparse, subprocess, sys, tempfile, os, json
try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

BROKER_URL  = "http://20.127.53.240:5000/access-request"
VM_HOST     = "20.127.53.240"
VM_USER     = "azureuser"
PRIVATE_KEY = os.path.expanduser("~/Desktop/jit-new-key")
PUBLIC_KEY  = os.path.expanduser("~/Desktop/jit-new-key.pub")
LOCAL_USER  = os.environ.get("USERNAME", "user")

def banner():
    print("\n" + "="*55)
    print("  JIT Access Broker — Just-In-Time SSH Access")
    print("="*55)

def request_access(reason, minutes):
    with open(PUBLIC_KEY, "r") as f:
        pub_key = f.read().strip()

    print(f"\n[1/4] Requesting access...")
    print(f"      User   : {LOCAL_USER}")
    print(f"      Reason : {reason}")
    print(f"      Duration: {minutes} minutes")

    resp = requests.post(BROKER_URL, json={
        "user":       LOCAL_USER,
        "reason":     reason,
        "minutes":    minutes,
        "public_key": pub_key
    })

    if resp.status_code != 200:
        print(f"\n❌ Broker denied: {resp.text}")
        sys.exit(1)

    return resp.json()

def save_cert(certificate):
    cert_path = os.path.expanduser("~/Desktop/jit-new-key-cert.pub")
    with open(cert_path, "w") as f:
        f.write(certificate)
    print(f"\n[2/4] Certificate saved → {cert_path}")
    return cert_path

def show_grant(data):
    print(f"\n[3/4] Access granted!")
    print(f"      NSG rule  : {data['nsg_rule']}")
    print(f"      Expires at: {data['expires_at']}")
    print(f"      Message   : {data['message']}")

def ssh_in():
    print(f"\n[4/4] Connecting to {VM_HOST}...")
    print("="*55 + "\n")
    subprocess.run([
        "ssh",
        "-i", PRIVATE_KEY,
        f"{VM_USER}@{VM_HOST}"
    ])

def main():
    parser = argparse.ArgumentParser(
        description="JIT Access Broker CLI — Request temporary SSH access"
    )
    parser.add_argument("--reason",  required=True, help="Reason for access request")
    parser.add_argument("--minutes", type=int, default=15, help="Access duration (max 15)")
    args = parser.parse_args()

    banner()
    data     = request_access(args.reason, args.minutes)
    cert_path = save_cert(data["certificate"])
    show_grant(data)
    ssh_in()

if __name__ == "__main__":
    main()
