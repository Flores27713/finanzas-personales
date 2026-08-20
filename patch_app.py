import re

with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

# 1. Add imports
imports = '''import os
import json
import base64
import jwt
from datetime import datetime, timedelta, timezone
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional'''

app_py = re.sub(r'import os.*?from typing import Optional', imports, app_py, flags=re.DOTALL)

# 2. Add SlowAPI Limiter and App init
app_init = '''limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Sistema de Gestión de Finanzas Personales Multi-Usuario",
    description="API & App Web para el control diario de presupuesto con autenticación y Google Login.",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)'''

app_py = re.sub(r'app = FastAPI\([^)]*\)', app_init, app_py, flags=re.DOTALL)

# 3. Handle APP_PIN, SECRET_KEY, GOOGLE_CLIENT_ID
env_vars = '''# Configuración de PIN de Seguridad de Respaldo
APP_PIN = os.getenv("APP_PIN")
if not APP_PIN:
    print("[CRITICAL WARNING] APP_PIN no está configurado. La aplicación podría ser vulnerable o fallar.")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt'''

app_py = re.sub(r'# Configuración de PIN de Seguridad de Respaldo.*?\nAPP_PIN = os\.getenv\("APP_PIN", "2771"\)', env_vars, app_py, flags=re.DOTALL)

# 4. Update get_current_user
get_curr_user_old = '''def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_str = auth_header.split(" ")[1]
        try:
            uid = int(token_str)
            u = crud.get_user_by_id(db, uid)
            if u:
                return u
        except ValueError:
            pass

    custom_uid = request.headers.get("x-app-user-id")
    if custom_uid:
        try:
            uid = int(custom_uid)
            u = crud.get_user_by_id(db, uid)
            if u:
                return u
        except ValueError:
            pass
            
    user_pin = request.headers.get("x-app-pin") or request.query_params.get("pin")
    if user_pin == APP_PIN:
        def_user = get_or_create_default_user(db)
        if def_user:
            return def_user

    raise HTTPException(status_code=401, detail="No autenticado")'''

get_curr_user_new = '''def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_str = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
            uid = payload.get("user_id")
            if uid is not None:
                u = crud.get_user_by_id(db, uid)
                if u:
                    return u
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Sesión expirada. Por favor inicia sesión nuevamente.")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Token inválido")

    raise HTTPException(status_code=401, detail="No autenticado")'''

app_py = app_py.replace(get_curr_user_old, get_curr_user_new)

# 5. Fix check_pin
check_pin_old = '''@app.post("/api/verify-pin")
def check_pin(login: schemas.PinLogin, db: Session = Depends(get_db)):
    if login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    user = get_or_create_default_user(db)
    return {"access_token": str(user.id), "user": user}'''

check_pin_new = '''@app.post("/api/verify-pin")
@limiter.limit("5/minute")
def check_pin(request: Request, login: schemas.PinLogin, db: Session = Depends(get_db)):
    if not APP_PIN or login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    user = get_or_create_default_user(db)
    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "user": user}'''

app_py = app_py.replace(check_pin_old, check_pin_new)

# 6. Fix login and register to return JWT
login_old = '''@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user_email(db, login_data.email, login_data.password)
    return {"access_token": str(user.id), "user": user}'''

login_new = '''@app.post("/api/auth/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user_email(db, login_data.email, login_data.password)
    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "user": user}'''

app_py = app_py.replace(login_old, login_new)

register_old = '''@app.post("/api/auth/register", response_model=schemas.TokenResponse, status_code=201)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, user_data.email)
    if user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    new_user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    return {"access_token": str(new_user.id), "user": new_user}'''

register_new = '''@app.post("/api/auth/register", response_model=schemas.TokenResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, user_data.email)
    if user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    new_user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    token = create_access_token({"user_id": new_user.id})
    return {"access_token": token, "user": new_user}'''

app_py = app_py.replace(register_old, register_new)

# 7. Fix google_auth and remove google-fast
with open('app_py_patched.py', 'w', encoding='utf-8') as f:
    f.write(app_py)
