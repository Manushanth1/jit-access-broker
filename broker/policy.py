ALLOWED_USERS = ["azureuser", "manu"]
MAX_DURATION_MINUTES = 15

def check(user, minutes):
    if user not in ALLOWED_USERS:
        return False, f"User '{user}' is not in the allowed list"
    if minutes > MAX_DURATION_MINUTES:
        return False, f"Requested {minutes}m exceeds max {MAX_DURATION_MINUTES}m"
    return True, "OK"
