#!/usr/bin/env python3
"""
JIT Access Broker - Audit Script
Lists all recorded sessions from Azure Blob Storage.
Usage: python jit-audit.py
       python jit-audit.py --download session-20260904-123456-789.log
"""
import argparse, sys, os
try:
    from azure.identity import AzureCliCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install",
                   "azure-identity", "azure-storage-blob", "-q"])
    from azure.identity import AzureCliCredential
    from azure.storage.blob import BlobServiceClient

STORAGE_ACCOUNT = "jitsessions"
CONTAINER       = "sessions"

def get_client():
    credential = AzureCliCredential()
    url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
    return BlobServiceClient(account_url=url, credential=credential)

def list_sessions():
    client = get_client()
    container = client.get_container_client(CONTAINER)

    print("\n" + "="*65)
    print("  JIT Access Broker — Session Audit Log")
    print("="*65)
    print(f"  Storage : {STORAGE_ACCOUNT}.blob.core.windows.net")
    print(f"  Container: {CONTAINER}")
    print("="*65)

    blobs = list(container.list_blobs())
    if not blobs:
        print("\n  No sessions recorded yet.\n")
        return

    print(f"\n  {'SESSION FILE':<45} {'SIZE':>8}  {'LAST MODIFIED'}")
    print(f"  {'-'*45} {'-'*8}  {'-'*20}")

    for blob in sorted(blobs, key=lambda b: b.last_modified, reverse=True):
        size = f"{blob.size:,} B"
        modified = blob.last_modified.strftime("%Y-%m-%d %H:%M UTC")
        print(f"  {blob.name:<45} {size:>8}  {modified}")

    print(f"\n  Total: {len(blobs)} session(s)\n")

def download_session(filename):
    client = get_client()
    blob = client.get_blob_client(container=CONTAINER, blob=filename)
    content = blob.download_blob().readall().decode("utf-8", errors="replace")

    print(f"\n{'='*65}")
    print(f"  Session: {filename}")
    print(f"{'='*65}\n")
    print(content)

def main():
    parser = argparse.ArgumentParser(description="JIT Broker Audit — View session recordings")
    parser.add_argument("--download", help="Download and print a specific session log")
    args = parser.parse_args()

    if args.download:
        download_session(args.download)
    else:
        list_sessions()

if __name__ == "__main__":
    main()
