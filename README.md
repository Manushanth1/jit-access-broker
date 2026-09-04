# JIT Access Broker

> **Just-In-Time SSH access on Azure** — zero standing access, time-limited certificates, automatic session recording.

Built as a DevOps portfolio project to demonstrate SSH certificate authority, dynamic NSG management, Managed Identity, Key Vault, and Azure Blob Storage.

---

## Architecture

```
Client CLI (jit-request.py)
        |
        | POST /access-request
        v
Broker API (Flask on Azure VM)
        |
        +---> policy.py    (allowlist + duration check)
        |
        +---> ca.py        (fetch CA key from Key Vault, sign SSH cert)
        |
        +---> nsg.py       (open scoped NSG rule via Managed Identity)
        |
        v
Return: {certificate, nsg_rule, expires_at}
        |
        v
SSH in with certificate (auto-expires in N minutes)
        |
        v
ForceCommand: script records session -> upload to Blob Storage
        |
        v
Reaper (systemd timer, 60s): delete expired NSG rules
```

---

## Azure Resources

| Resource | Purpose |
|---|---|
| `jit-vm` (Ubuntu 24.04, B1s) | Runs broker + target for JIT SSH |
| `jit-nsg` | Subnet NSG — denies port 22 by default |
| `jit-kv` (Key Vault) | Stores CA private key as secret |
| `jitsessions` (Storage) | Stores session recordings |
| `jit-broker-identity` (Managed Identity) | Broker authenticates to Azure APIs without credentials |

---

## Security Model

| Layer | Mechanism |
|---|---|
| Network | NSG denies port 22 — closed by default |
| Auth | SSH certificates signed by CA — auto-expire |
| Policy | Allowlist + max duration enforced by broker |
| Audit | Every session recorded + uploaded to Blob Storage |

---

## Files

```
broker/
  broker.py     Flask API — POST /access-request
  ca.py         Fetch CA key from Key Vault, sign certificate
  nsg.py        Create/delete NSG rules via Managed Identity
  policy.py     User allowlist and duration validation

jit-request.py  CLI client — request access and auto SSH in
jit-audit.py    Audit script — list/download session recordings
```

---

## Usage

### Request JIT access (1 command)
```bash
python jit-request.py --reason "fix nginx crash" --minutes 15
```

### View audit trail
```bash
python jit-audit.py
python jit-audit.py --download session-20260904-134515-53322.log
```

---

## Setup Summary

1. Azure VM with Managed Identity attached
2. Key Vault with CA private key (`ssh-ca-private-key` secret)
3. NSG with `deny-ssh` rule at priority 300
4. `TrustedUserCAKeys` configured on sshd
5. Broker running as systemd service on port 5000
6. Reaper running as systemd timer (every 60 seconds)
7. ForceCommand configured for session recording

---

## Tech Stack

- **Azure**: VM, NSG, Key Vault, Blob Storage, Managed Identity
- **Python**: Flask, azure-identity, azure-keyvault-secrets, azure-mgmt-network, azure-storage-blob
- **Linux**: systemd, ssh-keygen, script utility, fail2ban
- **Protocol**: SSH certificates (OpenSSH CA)

---

## Interview Talking Points

> *"A VM you cannot SSH into is the correct starting position. One POST request and 20 seconds later you are inside. 15 minutes later you are locked out again, the session is in Blob Storage, and the NSG is back to deny. That is JIT access."*
