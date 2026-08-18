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
from seed import seed_database, INITIAL_ACCOUNTS, INITIAL_CATEGORIES


from sqlalchemy import text

def run_auto_migrations():
    Base.metadata.create_all(bind=engine)
    
    for table in ["account", "category", "transaction"]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER;"))
        except Exception:
            pass

    for col, col_type in [("bank_name", "VARCHAR DEFAULT 'BancoEstado'"), ("account_type", "VARCHAR DEFAULT 'Cuenta Vista'")]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE account ADD COLUMN {col} {col_type};"))
        except Exception:
            pass

    for col, col_type in [("is_admin", "BOOLEAN DEFAULT FALSE"), ("monthly_income", "FLOAT DEFAULT 0.0"), ("onboarding_completed", "BOOLEAN DEFAULT FALSE"), ("quick_buttons_json", "VARCHAR")]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type};"))
        except Exception:
            pass

    for table in ["account", "category", "transaction"]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"UPDATE {table} SET user_id = 1 WHERE user_id IS NULL;"))
        except Exception:
            pass




try:
    run_auto_migrations()
except Exception as e:
    print("[MIGRATION SETUP NOTICE]", e)

Base.metadata.create_all(bind=engine)

# Configuración de PIN de Seguridad de Respaldo (por defecto: 2771)
APP_PIN = os.getenv("APP_PIN", "2771")

def get_or_create_default_user(db: Session):
    user = db.query(models.User).filter(models.User.email == "omar@finanzas.local").first()
    if not user:
        user = db.query(models.User).filter(models.User.name == "Omar").first()
    if not user:
        user = db.query(models.User).filter(models.User.id == 1).first()
    if not user:
        user = crud.create_user_with_defaults(
            db, name="Omar", email="omar@finanzas.local", password=APP_PIN
        )
    if not user.is_admin:
        user.is_admin = True
        db.commit()
    crud.ensure_user_defaults(db, user.id)
    return user







# Inyección de Dependencia para Identificar al Usuario Autenticado
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
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
    u_id = user.id if user else 1
    u_name = user.name if user else "Omar"
    return {"status": "ok", "message": "Acceso concedido", "user_id": u_id, "name": u_name}


# ==========================================
# ENDPOINTS DE ADMINISTRACIÓN & ONBOARDING
# ==========================================
@app.get("/api/admin/users")
def list_users_admin(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requieren permisos de administrador.")
    return crud.get_all_users_admin(db)

@app.delete("/api/admin/users/{target_id}")
def delete_user_admin(target_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requieren permisos de administrador.")
    return crud.delete_user_admin(db, target_id, current_user.id)

@app.post("/api/onboarding")
def complete_onboarding(data: schemas.OnboardingRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.complete_onboarding(db, current_user.id, data)

@app.post("/api/user/quick-buttons")
def update_quick_buttons(data: schemas.QuickButtonsUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    buttons = [b.model_dump() for b in data.quick_buttons]
    return crud.update_user_quick_buttons(db, current_user.id, buttons)

@app.post("/api/accounts", response_model=schemas.AccountResponse)
def create_account(acc_data: schemas.AccountCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_user_account(db, current_user.id, acc_data)






@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    if not user:
        user = crud.get_user_by_email(db, user_data.email)

    u_id = user.id if user else 1
    return {
        "access_token": str(u_id),
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

        user = user or crud.get_user_by_email(db, email)
        u_id = user.id if user else 1
        return {
            "access_token": str(u_id),
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al verificar credenciales de Google: {str(e)}")


@app.post("/api/auth/google-fast", response_model=schemas.TokenResponse)
def google_fast_auth(fast_data: schemas.GoogleFastAuth, db: Session = Depends(get_db)):
    """
    Inicio de sesión rápido con correo de Google (1-Clic).
    """
    email = fast_data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Por favor ingresa un correo de Google válido")

    name = fast_data.name or email.split("@")[0].capitalize()
    picture = f"https://ui-avatars.com/api/?name={name}&background=14b8a6&color=fff"

    user = crud.get_user_by_email(db, email)
    if not user:
        user = crud.create_user_with_defaults(
            db, name=name, email=email, picture=picture
        )
    else:
        if picture and not user.picture:
            user.picture = picture
            db.commit()

    user = user or crud.get_user_by_email(db, email)
    u_id = user.id if user else 1
    return {
        "access_token": str(u_id),
        "token_type": "bearer",
        "user": user
    }




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
    return crud.record_expense(db, expense, user_id=current_user.id if current_user else 1)


@app.post("/transactions/transfer", response_model=schemas.TransactionResponse, status_code=201)
def create_transfer(
    transfer: schemas.TransferCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.record_transfer(db, transfer, user_id=current_user.id if current_user else 1)


@app.post("/transactions/income", response_model=schemas.TransactionResponse, status_code=201)
def create_income(
    income: schemas.IncomeCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.record_income(db, income, user_id=current_user.id if current_user else 1)


@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.delete_transaction(db, transaction_id, user_id=current_user.id if current_user else 1)



@app.get("/dashboard", response_model=schemas.DashboardSummary)
def get_dashboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_dashboard_summary(db, user_id=current_user.id if current_user else 1
)


@app.get("/api/accounts", response_model=list[schemas.AccountResponse])
def read_accounts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_accounts(db, user_id=current_user.id if current_user else 1
)


@app.get("/api/categories", response_model=list[schemas.CategoryResponse])
def read_categories(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_categories(db, user_id=current_user.id if current_user else 1)

@app.post("/api/categories", response_model=schemas.CategoryResponse, status_code=201)
def create_category(
    category: schemas.CategoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.create_category(db, category, user_id=current_user.id if current_user else 1)


@app.get("/api/transactions")
def read_transactions(
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_recent_transactions(db, user_id=current_user.id if current_user else 1
, limit=limit)


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
    return crud.get_monthly_report(db, user_id=current_user.id if current_user else 1, year=year, month=month)


@app.post("/api/reset-database")
def reset_database(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.reset_database(db, user_id=current_user.id if current_user else 1)



# Servidor directo si se ejecuta 'python app.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
