"""Password hashing and signed tokens (stdlib only)."""
import hashlib
import hmac
import os

SECRET = b"fixture-secret"


def _sign(payload):
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()


def hash_password(password, salt=None):
    """Return "salt$digest" for the password; a random salt is used if none is given."""
    salt = salt if salt is not None else os.urandom(8).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 1000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    """Check a password against a value produced by hash_password."""
    salt, _, _ = stored.partition("$")
    return hmac.compare_digest(hash_password(password, salt), stored)


def issue_token(user, expires_at):
    """Create a "user:expires:signature" token."""
    payload = f"{user}:{int(expires_at)}"
    return f"{payload}:{_sign(payload)}"


def validate_token(token, now):
    """Return the user name if the token is genuine and not expired, else None."""
    try:
        user, expires, signature = token.split(":")
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(f"{user}:{expires}")):
        return None
    return user if int(expires) > now else None
