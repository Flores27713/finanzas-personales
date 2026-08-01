import os
import json
import base64
from fastapi import FastAPI, Depends, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
import schemas
import crud
from database import engine, get_db, Base
from seed import seed_database

# Inicializar Tablas en la Base de Datos SQLite/PostgreSQL si no existen
Base.metadata.create_all(bind=engine)

# Configuración de PIN de Seguridad de Respaldo (por defecto: 2771)
APP_PIN = os.getenv("APP_PIN", "2771")


# Helper para obtener o crear el usuario predeterminado de respaldo (PIN Login / Legacy)
def get_or_create_default_user(db: Session):
    user = crud.get_user_by_email(db, "omar@finanzas.local")
    if not user:
        user = crud.create_user_with_defaults(
            db, name="Omar", email="omar@finanzas.local", password=APP_PIN
        )

        # Migrar datos huérfanos sin user_id al usuario Omar si existieran
        db.query(models.Account).filter(models.Account.user_id == None).update({"user_id": user.id})
        db.query(models.Category).filter(models.Category.user_id == None).update({"user_id": user.id})
        db.query(models.Transaction).filter(models.Transaction.user_id == None).update({"user_id": user.id})
        db.commit()

    return user


# Inyección de Dependencia para Identificar al Usuario Autenticado
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    # 1. Verificar encabezado Authorization (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        user_id_str = auth_header.split(" ")[1]
        try:
            user_id = int(user_id_str)
            user = crud.get_user_by_id(db, user_id)
            if user:
                return user
        except ValueError:
            pass

    # 2. Verificar encabezado x-app-user-id
    custom_uid = request.headers.get("x-app-user-id")
    if custom_uid:
        try:
            user_id = int(custom_uid)
            user = crud.get_user_by_id(db, user_id)
            if user:
                return user
        except ValueError:
            pass

    # 3. Soporte para PIN Legacy o parámetro pin (asigna al usuario Omar)
    user_pin = request.headers.get("x-app-pin") or request.query_params.get("pin")
    if user_pin == APP_PIN:
        return get_or_create_default_user(db)

    raise HTTPException(status_code=401, detail="No autorizado. Inicia sesión o ingresa tu PIN.")


# Crear App FastAPI
app = FastAPI(
    title="Sistema de Gestión de Finanzas Personales Multi-Usuario",
    description="API & App Web para el control diario de presupuesto con autenticación y Google Login.",
    version="2.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ==========================================
# RUTAS DE INTERFAZ DE USUARIO (FRONTEND)
# ==========================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ==========================================
# ENDPOINTS DE AUTENTICACIÓN & USUARIOS
# ==========================================
@app.post("/api/verify-pin")
def check_pin(login: schemas.PinLogin, db: Session = Depends(get_db)):
    if login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    user = get_or_create_default_user(db)
    return {"status": "ok", "message": "Acceso concedido", "user_id": user.id, "name": user.name}


@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    return {
        "access_token": str(user.id),
        "token_type": "bearer",
        "user": user
    }


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login_user(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user_email(db, email=login_data.email, password=login_data.password)
    return {
        "access_token": str(user.id),
        "token_type": "bearer",
        "user": user
    }


@app.post("/api/auth/google", response_model=schemas.TokenResponse)
def google_auth(google_data: schemas.GoogleAuth, db: Session = Depends(get_db)):
    """
    Recibe el ID Token JWT generado por Google Sign-In, extrae el correo y perfil, y autentica al usuario.
    """
    token = google_data.credential
    try:
        # Decodificar payload no firmado del JWT de Google
        parts = token.split(".")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Token de Google inválido")
        
        payload_b64 = parts[1]
        # Ajustar padding Base64 si es necesario
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.b64decode(payload_b64)
        data = json.loads(payload_bytes.decode("utf-8"))

        email = data.get("email")
        name = data.get("name") or email.split("@")[0]
        google_id = data.get("sub")
        picture = data.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="El token de Google no contiene un correo válido")

        # Buscar usuario por email o google_id
        user = crud.get_user_by_email(db, email)
        if not user:
            user = crud.create_user_with_defaults(
                db, name=name, email=email, google_id=google_id, picture=picture
            )
        else:
            if not user.google_id:
                user.google_id = google_id
            if picture:
                user.picture = picture
            db.commit()

        return {
            "access_token": str(user.id),
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al verificar credenciales de Google: {str(e)}")


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ==========================================
# ENDPOINTS PRINCIPALES (PROTEGIDOS POR USUARIO)
# ==========================================
@app.post("/transactions/expense", response_model=schemas.TransactionResponse, status_code=201)
def create_expense(
    expense: schemas.ExpenseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.record_expense(db, expense, user_id=current_user.id)


@app.post("/transactions/transfer", response_model=schemas.TransactionResponse, status_code=201)
def create_transfer(
    transfer: schemas.TransferCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.record_transfer(db, transfer, user_id=current_user.id)


@app.post("/transactions/income", response_model=schemas.TransactionResponse, status_code=201)
def create_income(
    income: schemas.IncomeCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.record_income(db, income, user_id=current_user.id)


@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.delete_transaction(db, transaction_id, user_id=current_user.id)


@app.get("/dashboard", response_model=schemas.DashboardSummary)
def get_dashboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_dashboard_summary(db, user_id=current_user.id)


@app.get("/api/accounts", response_model=list[schemas.AccountResponse])
def read_accounts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_accounts(db, user_id=current_user.id)


@app.get("/api/categories", response_model=list[schemas.CategoryResponse])
def read_categories(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_categories(db, user_id=current_user.id)


@app.get("/api/transactions")
def read_transactions(
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_recent_transactions(db, user_id=current_user.id, limit=limit)


@app.get("/api/monthly-report")
def get_monthly_report(
    year: int = None,
    month: int = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import datetime
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    return crud.get_monthly_report(db, user_id=current_user.id, year=year, month=month)


@app.post("/api/reset-database")
def reset_database(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.reset_database(db, user_id=current_user.id)


# Servidor directo si se ejecuta 'python app.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
