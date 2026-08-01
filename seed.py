from sqlalchemy.orm import Session
import models

INITIAL_ACCOUNTS = [
    {"name": "CuentaRUT", "balance": 120000.0},
    {"name": "Mercado Pago Disponible", "balance": 70000.0},
    {"name": "Mercado Pago Ahorro", "balance": 150000.0},
    {"name": "Efectivo (Billetera)", "balance": 0.0},
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
    Asegura la creación automática de la cuenta 'Efectivo (Billetera)'.
    """
    for acc in INITIAL_ACCOUNTS:
        existing = db.query(models.Account).filter(models.Account.name == acc["name"]).first()
        if not existing:
            account_obj = models.Account(name=acc["name"], balance=acc["balance"])
            db.add(account_obj)
            print(f"[SEED] Cuenta creada: {acc['name']}")

    for cat in INITIAL_CATEGORIES:
        existing = db.query(models.Category).filter(models.Category.name == cat["name"]).first()
        if not existing:
            cat_obj = models.Category(name=cat["name"], monthly_budget=cat["monthly_budget"])
            db.add(cat_obj)
            print(f"[SEED] Categoría creada: {cat['name']}")

    db.commit()
