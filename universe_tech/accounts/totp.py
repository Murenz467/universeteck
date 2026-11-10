"""Time-based one-time passwords (RFC 6238), compatible with Google Authenticator, Microsoft Authenticator, Authy..."""
import base64
import hashlib
import hmac
import secrets
import struct
import time

STEP = 30


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret, counter):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def verify(secret, token, last_step=0, window=1, now=None):
    """Return the matching time-step if the code is valid and newer than the last accepted one (blocks replay)."""
    token = (token or "").strip().replace(" ", "")
    if len(token) != 6 or not token.isdigit():
        return None
    current = int((now if now is not None else time.time()) // STEP)
    for step in range(current - window, current + window + 1):
        if step > last_step and hmac.compare_digest(_code(secret, step), token):
            return step
    return None


def provisioning_uri(secret, account, issuer="Universe Tech"):
    from urllib.parse import quote
    return (f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm=SHA1&digits=6&period={STEP}")


def current_code(secret, now=None):
    return _code(secret, int((now if now is not None else time.time()) // STEP))
