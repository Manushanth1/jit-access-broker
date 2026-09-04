# JIT Access Broker — Design Spec

**Project 3 of 3 · Azure · ~45 hours over 3 weeks · Target spend: under $2**

Zero standing SSH privilege. Access is requested, time-boxed, recorded, revoked
automatically, and summarized in plain English.

---

## 1. The problem it solves

Everyone has permanent SSH access to production. Keys were handed out eighteen
months ago and nobody remembers to whom. When something changes on a box, nobody
can say who did it or why.

## 2. Why it's a strong third project

It is security-flavoured, which is highly hireable. It is genuinely Azure-native —
VNets, NSGs, Managed Identity, Key Vault, Blob Storage, Azure Monitor, Entra ID —
so it doubles as your AZ-104 lab. And it makes SSH a *depth* topic rather than a
line on your CV: short-lived SSH certificates are something most junior candidates
have never touched, and they are conceptually simple once seen.

It also runs on the free B1s VM, which makes it your **always-on, always-demoable**
project — the URL still works when a recruiter clicks it three weeks later.

## 3. Success criteria

1. No standing access: the NSG denies port 22 by default and the VM has no `authorized_keys` file.
2. From request to connected shell in under 60 seconds.
3. Certificates expire on their own. **Demonstrate that an expired cert is rejected.**
4. The NSG rule is revoked at expiry even if the broker crashes.
5. Every session is recorded, shipped to Blob Storage, and summarized in plain English.
6. All infrastructure is Terraform-managed. Azure spend stays under $2.

## 4. The access lifecycle

```
request    →   approve   →   grant        →   session     →   expire      →   audit
                                                                              
POST           policy        NSG rule +       ssh -i cert     NSG rule        LLM summary
/access-       check         15-min SSH       session         removed,        → Blob +
request                      certificate      recorded        cert dead       audit log

~2s            ~1s           ~20s             ≤ 15 min        automatic       ~5s
```

Everything after "grant" happens without a human. That is the point — the system
does not depend on anyone remembering to clean up.

## 5. Architecture

```
broker  (Python, systemd unit on the free B1s VM)
  ├── POST /access-request   {user, reason, minutes}
  ├── policy.py    time window · max duration · allowed users (Entra group)
  ├── ca.py        ssh-keygen -s → cert valid 15 min, principals pinned
  ├── nsg.py       add allow rule, source = requester IP, tag = absolute UTC expiry
  ├── reaper.py    systemd timer, every 60s: delete rules whose expiry has passed
  └── audit.py     session recording → LLM → plain-English entry → Blob Storage

target VM  (hardened)
  ├── sshd: TrustedUserCAKeys set, PasswordAuthentication no, no authorized_keys
  ├── session recording: ForceCommand wrapper using `script`
  └── log shipper → Blob Storage (hot → cool 30d → archive 90d)
```

The reaper is the part worth explaining in an interview. It exists because the
broker might crash between opening a rule and closing it. Cleanup that depends on
the happy path isn't cleanup.

## 6. Milestones

### Week 1 — Foundation and hardening (15h)

- **1.1 (3h)** Azure setup. **Budget alerts at $2 and $5 first.** Managed Identity,
  Terraform backend in a Storage Account.
- **1.2 (5h)** Terraform: VNet, subnet, NSG denying 22 by default, B1s Ubuntu VM,
  Managed Identity, Key Vault, Storage Account with lifecycle rules
  (hot → cool at 30 days → archive at 90 days).
- **1.3 (4h)** Linux hardening via cloud-init: no password auth, no root login,
  `fail2ban`, unattended upgrades, sysctl basics.
- **1.4 (3h)** Verify that SSH from your laptop is refused, and write down exactly
  why — NSG deny *and* no `authorized_keys`. Two independent controls.

**Exit:** a VM you cannot SSH into. That's the correct starting position.

### Week 2 — The broker (15h)

- **2.1 (4h)** SSH certificate authority. Generate the CA keypair, store the private
  key in Key Vault, set `TrustedUserCAKeys` on the VM, sign a certificate by hand
  and connect. **Prove that `-V +2m` actually rejects after two minutes.**
- **2.2 (5h)** Broker service: policy check → sign certificate → open an NSG rule
  scoped to the requester's source IP → return the certificate. Postman collection
  for the API.
- **2.3 (3h)** Reaper: systemd timer every 60 seconds, deleting NSG rules whose
  expiry tag has passed. Idempotent — safe to run twice on the same rule.
- **2.4 (3h)** Session recording: `ForceCommand` wrapper using `script`, output to
  `/var/log/sessions`, shipped to Blob on session close.

**Exit:** request → connect → fifteen minutes later the connection dies and the NSG rule is gone.

### Week 3 — Audit, Azure depth, polish (15h)

- **3.1 (4h)** `audit.py`: read the recorded session, LLM →
  `{summary, commands_run, risk_flags[], files_touched}`. Flag `sudo`, `systemctl`,
  edits under `/etc`, package installs, and curl-piped-to-shell.
- **3.2 (4h)** Blob lifecycle plus a SAS-token download flow for auditors. Ship
  broker logs to Azure Monitor and write a KQL query answering
  *"who accessed what last week."*
- **3.3 (3h)** GitHub Actions: `terraform plan` on PR, `apply` on merge, using OIDC to Azure.
- **3.4 (4h)** README with the lifecycle diagram, 3-minute demo, and a threat-model
  section — what this stops and what it doesn't.

**Exit:** the full lifecycle demo runs, the audit entry lands in Blob, and the KQL query returns it.

## 7. Cost guards

| Resource | Free-tier position |
|----------|--------------------|
| B1s Linux VM | 750 hours/month for 12 months — **one VM only** |
| VNet, NSG | Free |
| Key Vault | ~$0.03 per 10,000 operations — negligible |
| Blob Storage | A few MB. Under $0.05 |
| Azure Monitor | 5 GB/month ingest free — session logs are tiny, but cap them anyway |

Budget alerts at **$2 and $5**, set up in milestone 1.1. Expected total: **under $2**.

## 8. The demo script

| Time | Beat |
|------|------|
| 0:00 | `ssh azureuser@vm` → connection refused. "There is no standing access." |
| 0:20 | POST the access request via Postman. Reason: "restart nginx". Duration: 15 minutes. |
| 0:35 | Response contains a short-lived certificate. `ssh-keygen -L -f cert` shows the validity window. |
| 0:55 | Connect. Run `sudo systemctl restart nginx`, edit `/etc/hosts`. |
| 1:30 | Show the NSG rule in the portal — scoped to your IP, tagged with its expiry. |
| 1:50 | The reaper removes the rule. The session dies. |
| 2:15 | Blob Storage: the audit entry. "Restarted nginx and edited /etc/hosts. 2 commands flagged elevated-risk." |
| 2:40 | KQL in Azure Monitor: all access in the last seven days. |

## 9. Interview talking points

- SSH certificates versus `authorized_keys` — why certificate authorities scale and key files don't.
- What the reaper protects against, and why cleanup on the happy path isn't cleanup.
- **Threat model.** Stops: standing access, key sprawl, unattributed sessions.
  Doesn't stop: a malicious user *during* their window, or a compromised CA key.
  Knowing the limits of your own control is the answer that impresses.
- Why the CA private key lives in Key Vault, and what your response would be if it leaked.
- Blob lifecycle tiers, and why archive at 90 days.
- AZ-104 crossover: NSG versus Azure Firewall; Managed Identity versus service principal.

## 10. Known risks

1. **SSH CA setup** — the `TrustedUserCAKeys` path and sshd restart. Budget 3 hours. Debug with `ssh -vvv`.
2. **`ForceCommand` can lock you out of your own VM.** Keep the Azure Serial Console
   open in a second tab while developing this. This is the one that bites people.
3. **NSG rule priority collisions** — reserve a dedicated priority range (200–299) for JIT rules.
4. **Reaper race conditions** — tag with absolute UTC expiry and make deletion idempotent.
5. **B1s is 1 vCPU and 1 GB.** Do not try to run anything heavy on it.

## 11. AZ-104 coverage

| Exam domain | Weight | Covered here |
|-------------|--------|--------------|
| Identity & governance | 20–25% | Entra groups, RBAC, Managed Identity, Key Vault |
| Storage | 15–20% | Blob, lifecycle management, SAS tokens |
| Compute | 20–25% | VM deployment, cloud-init, VM extensions |
| Virtual networking | 15–20% | VNet, subnets, NSG rules and priorities |
| Monitoring | 10–15% | Azure Monitor ingestion, KQL queries |

Combined with Alert Autopsy's AKS work, the two Azure projects cover every AZ-104
domain with hands-on artifacts.

## 12. Explicitly out of scope

Windows and RDP targets, multi-VM fleets, an approval web UI (the API plus Postman
is enough), Privileged Identity Management integration, and full CIS benchmark
compliance.
