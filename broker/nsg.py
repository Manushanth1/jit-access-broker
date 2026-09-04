from azure.identity import ManagedIdentityCredential
from azure.mgmt.network import NetworkManagementClient
from datetime import datetime, timedelta, timezone
import uuid

SUBSCRIPTION_ID = "c607d94c-ac47-4e96-9c14-ee9c5b366058"
RESOURCE_GROUP  = "jit-access-rg"
NSG_NAME        = "jit-nsg"

def open_rule(source_ip: str, duration_minutes: int):
    credential = ManagedIdentityCredential()
    client = NetworkManagementClient(credential, SUBSCRIPTION_ID)

    expiry    = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    rule_name = f"jit-{uuid.uuid4().hex[:8]}"

    nsg  = client.network_security_groups.get(RESOURCE_GROUP, NSG_NAME)
    used = {r.priority for r in nsg.security_rules if 200 <= r.priority <= 299}
    priority = next(p for p in range(200, 300) if p not in used)

    client.security_rules.begin_create_or_update(
        RESOURCE_GROUP, NSG_NAME, rule_name,
        {
            "priority": priority,
            "protocol": "Tcp",
            "direction": "Inbound",
            "access": "Allow",
            "source_address_prefix": source_ip,
            "source_port_range": "*",
            "destination_address_prefix": "*",
            "destination_port_range": "22",
            "description": f"JIT expires {expiry.isoformat()}"
        }
    ).result()

    return rule_name, expiry.isoformat()
