from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import wraps
from flask import request,jsonify
import jwt
import os


load_dotenv()

SECRET_KEY=os.getenv('SECRET_KEY')
ALGORITHM='HS256'

def token_gen(user_id,username):
    payload={
        "user_id":user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=120),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)

def verify_token(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        token=None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.current_user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired."})
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."})
        return func(*args, **kwargs)
    return wrapper