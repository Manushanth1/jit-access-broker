import subprocess, tempfile, os
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

VAULT_URL   = "https://jit-kv.vault.azure.net"
SECRET_NAME = "ssh-ca-private-key"

def sign_certificate(user_pub_key: str, username: str, duration_minutes: int) -> str:
    credential = ManagedIdentityCredential()
    client = SecretClient(vault_url=VAULT_URL, credential=credential)
    ca_key = client.get_secret(SECRET_NAME).value

    with tempfile.TemporaryDirectory() as tmpdir:
        ca_path   = os.path.join(tmpdir, "ca")
        pub_path  = os.path.join(tmpdir, "user.pub")
        cert_path = os.path.join(tmpdir, "user-cert.pub")

        with open(ca_path, "w") as f:
            f.write(ca_key)
        os.chmod(ca_path, 0o600)

        with open(pub_path, "w") as f:
            f.write(user_pub_key)

        subprocess.run([
            "ssh-keygen", "-s", ca_path,
            "-I", f"jit-{username}",
            "-n", "azureuser",
            "-V", f"+{duration_minutes}m",
            pub_path
        ], check=True)

        with open(cert_path, "r") as f:
            return f.read()
