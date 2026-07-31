from sqlalchemy.orm import Session
import models

INITIAL_ACCOUNTS = [
    {"name": "CuentaRUT", "balance": 120000.0},
    {"name": "Mercado Pago Disponible", "balance": 70000.0},
    {"name": "Mercado Pago Ahorro", "balance": 150000.0},
]

INITIAL_CATEGORIES = [
    {"name": "Transporte Talca (Colectivo / Uber Trabajo)", "monthly_budget": 35000.0},
    {"name": "Transporte Interurbano (Bus Talca-Linares)", "monthly_budget": 40000.0},
    {"name": "Transporte Local Linares (Uber / Colectivos)", "monthly_budget": 20000.0},
    {"name": "Alimentación y Aseo (Feria / Mercado)", "monthly_budget": 80000.0},
    {"name": "Ocio y Citas (Salidas)", "monthly_budget": 30000.0},
    {"name": "Deudas / Compromisos", "monthly_budget": 50000.0},
    {"name": "Fondo Ahorro / Máster", "monthly_budget": 150000.0},
]

def seed_database(db: Session):
    """
    Precarga las cuentas y categorías iniciales si no existen en la base de datos.
    """
    # Verificar y sembrar Cuentas
    existing_accounts_count = db.query(models.Account).count()
    if existing_accounts_count == 0:
        for acc in INITIAL_ACCOUNTS:
            account_obj = models.Account(name=acc["name"], balance=acc["balance"])
            db.add(account_obj)
        db.commit()
        print("[SEED] 3 cuentas iniciales creadas con éxito.")
    else:
        print("[SEED] Cuentas ya existentes. Se omitió la precarga de cuentas.")

    # Verificar y sembrar Categorías
    existing_categories_count = db.query(models.Category).count()
    if existing_categories_count == 0:
        for cat in INITIAL_CATEGORIES:
            cat_obj = models.Category(name=cat["name"], monthly_budget=cat["monthly_budget"])
            db.add(cat_obj)
        db.commit()
        print("[SEED] 7 categorías iniciales creadas con éxito.")
    else:
        print("[SEED] Categorías ya existentes. Se omitió la precarga de categorías.")
