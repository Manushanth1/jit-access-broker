from flask import Flask, request, jsonify
import policy, ca, nsg

app = Flask(__name__)

@app.route("/access-request", methods=["POST"])
def access_request():
    data      = request.json
    user      = data.get("user", "")
    reason    = data.get("reason", "")
    minutes   = int(data.get("minutes", 15))
    pub_key   = data.get("public_key", "")
    source_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    allowed, msg = policy.check(user, minutes)
    if not allowed:
        return jsonify({"error": msg}), 403

    certificate = ca.sign_certificate(pub_key, user, minutes)
    rule_name, expiry = nsg.open_rule(source_ip, minutes)

    return jsonify({
        "certificate": certificate,
        "nsg_rule":    rule_name,
        "expires_at":  expiry,
        "message":     f"Access granted for {minutes} minutes. Reason: {reason}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
