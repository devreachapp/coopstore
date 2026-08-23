import os, secrets
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

def get_serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="download-salt")

from typing import Tuple
from datetime import datetime, timedelta
import secrets

def make_download_token(purchase_id: int, ttl_seconds: int = 24*3600) -> Tuple[str, datetime]:
    # create a random nonce that also gets stored in DB
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    return token, expires_at

def sign_payload(app, payload: dict) -> str:
    s = get_serializer(app.config['SECRET_KEY'])
    return s.dumps(payload)

def unsign_payload(app, token: str, max_age: int = 24*3600) -> dict:
    s = get_serializer(app.config['SECRET_KEY'])
    return s.loads(token, max_age=max_age)

