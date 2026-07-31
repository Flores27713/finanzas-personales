import os
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

# Inicializar Tablas en la Base de Datos SQLite si no existen
Base.metadata.create_all(bind=engine)

# Ejecutar el Seed inicial de Cuentas y Categorías
db_session = next(get_db())
try:
    seed_database(db_session)
finally:
    db_session.close()

# Configuración de PIN de Seguridad (por defecto: 2771 o configurable vía Variable de Entorno APP_PIN)
APP_PIN = os.getenv("APP_PIN", "2771")

def verify_pin(request: Request):
    user_pin = request.headers.get("x-app-pin") or request.query_params.get("pin")
    if not user_pin or user_pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto o no autorizado")
    return True


# Crear App FastAPI
app = FastAPI(
    title="Sistema de Gestión de Finanzas Personales",
    description="API & App Web para el control diario de presupuesto, cuentas y gastos hormiga.",
    version="1.0.0"
)

# Configurar motor de plantillas Jinja2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ==========================================
# RUTAS DE INTERFAZ DE USUARIO (FRONTEND)
# ==========================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root(request: Request):
    """
    Renderiza la interfaz web principal del sistema.
    """
    return templates.TemplateResponse(request=request, name="index.html")


# Endpoint público para verificar PIN de inicio de sesión
@app.post("/api/verify-pin")
def check_pin(login: schemas.PinLogin):
    """
    Verifica el PIN de acceso introducido por el usuario.
    """
    if login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    return {"status": "ok", "message": "Acceso concedido"}


# ==========================================
# ENDPOINTS PRINCIPALES (PROTEGIDOS POR PIN)
# ==========================================
@app.post("/transactions/expense", response_model=schemas.TransactionResponse, status_code=201, dependencies=[Depends(verify_pin)])
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    """
    Registrar un gasto: Descuenta automáticamente el monto del saldo de la cuenta seleccionada.
    """
    return crud.record_expense(db, expense)


@app.post("/transactions/transfer", response_model=schemas.TransactionResponse, status_code=201, dependencies=[Depends(verify_pin)])
def create_transfer(transfer: schemas.TransferCreate, db: Session = Depends(get_db)):
    """
    Mover saldo entre cuentas (ej. pasar $15.000 de MP Disponible a CuentaRUT).
    """
    return crud.record_transfer(db, transfer)


@app.post("/transactions/income", response_model=schemas.TransactionResponse, status_code=201, dependencies=[Depends(verify_pin)])
def create_income(income: schemas.IncomeCreate, db: Session = Depends(get_db)):
    """
    Registrar un ingreso de dinero (ej. Pago Evento DJ en efectivo o transferencia).
    """
    return crud.record_income(db, income)



@app.delete("/transactions/{transaction_id}", dependencies=[Depends(verify_pin)])
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """
    Eliminar una transacción errónea o duplicada y revertir automáticamente los saldos de las cuentas.
    """
    return crud.delete_transaction(db, transaction_id)



@app.get("/dashboard", response_model=schemas.DashboardSummary, dependencies=[Depends(verify_pin)])
def get_dashboard(db: Session = Depends(get_db)):
    """
    Retorna:
    1. Saldo actual consolidado de las 3 cuentas.
    2. Total gastado por categoría en el mes.
    3. Cálculo del límite diario disponible para gastos hormiga.
    """
    return crud.get_dashboard_summary(db)


# ==========================================
# ENDPOINTS COMPLEMENTARIOS DE APOYO (PROTEGIDOS POR PIN)
# ==========================================
@app.get("/api/accounts", response_model=list[schemas.AccountResponse], dependencies=[Depends(verify_pin)])
def read_accounts(db: Session = Depends(get_db)):
    """Obtener lista de cuentas y sus saldos."""
    return crud.get_accounts(db)


@app.get("/api/categories", response_model=list[schemas.CategoryResponse], dependencies=[Depends(verify_pin)])
def read_categories(db: Session = Depends(get_db)):
    """Obtener lista de categorías y presupuestos mensuales."""
    return crud.get_categories(db)


@app.get("/api/transactions", dependencies=[Depends(verify_pin)])
def read_transactions(limit: int = 20, db: Session = Depends(get_db)):
    """Obtener historial reciente de transacciones."""
    return crud.get_recent_transactions(db, limit=limit)


# Servidor directo si se ejecuta 'python app.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
