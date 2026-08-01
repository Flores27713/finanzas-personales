import calendar
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException

import models
import schemas
from seed import INITIAL_ACCOUNTS, INITIAL_CATEGORIES

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def hash_password(password: str) -> str:
    return hashlib.sha256((password + "finanzas_secret_salt_2026").encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


# ==========================================
# FUNCIONES DE USUARIO & AUTENTICACIÓN
# ==========================================
def get_user_by_email(db: Session, email: str):
    if not email:
        return None
    clean_email = email.strip().lower()
    return db.query(models.User).filter(models.User.email == clean_email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def ensure_user_defaults(db: Session, user_id: int):
    """Garantiza que el usuario tenga sus 4 cuentas y 6 categorías asociadas."""
    accounts = db.query(models.Account).filter(models.Account.user_id == user_id).all()
    if not accounts:
        for acc in INITIAL_ACCOUNTS:
            try:
                acc_obj = models.Account(user_id=user_id, name=acc["name"], balance=acc["balance"])
                db.add(acc_obj)
                db.commit()
            except Exception:
                db.rollback()

    categories = db.query(models.Category).filter(models.Category.user_id == user_id).all()
    if not categories:
        for cat in INITIAL_CATEGORIES:
            try:
                cat_obj = models.Category(user_id=user_id, name=cat["name"], monthly_budget=cat["monthly_budget"])
                db.add(cat_obj)
                db.commit()
            except Exception:
                db.rollback()


def create_user_with_defaults(db: Session, name: str, email: str, password: str = None, google_id: str = None, picture: str = None):
    clean_email = email.strip().lower()
    
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if user:
        ensure_user_defaults(db, user.id)
        return user

    hashed_pw = hash_password(password) if password else None

    db_user = models.User(
        name=name.strip(),
        email=clean_email,
        hashed_password=hashed_pw,
        google_id=google_id,
        picture=picture
    )

    try:
        db.add(db_user)
        db.commit()
    except Exception:
        db.rollback()
        user = db.query(models.User).filter(models.User.email == clean_email).first()
        if user:
            ensure_user_defaults(db, user.id)
            return user
        return db.query(models.User).first()

    ensure_user_defaults(db, db_user.id)
    return db_user


def authenticate_user_email(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
    ensure_user_defaults(db, user.id)
    return user

import json

def get_all_users_admin(db: Session):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    result = []
    for u in users:
        acc_count = db.query(models.Account).filter(models.Account.user_id == u.id).count()
        tx_count = db.query(models.Transaction).filter(models.Transaction.user_id == u.id).count()
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_admin": u.is_admin,
            "monthly_income": u.monthly_income,
            "onboarding_completed": u.onboarding_completed,
            "created_at": u.created_at,
            "account_count": acc_count,
            "transaction_count": tx_count
        })
    return result

def delete_user_admin(db: Session, target_user_id: int, current_admin_id: int):
    if target_user_id == current_admin_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador principal.")

    target_user = get_user_by_id(db, target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    db.query(models.Transaction).filter(models.Transaction.user_id == target_user_id).delete(synchronize_session=False)
    db.query(models.Account).filter(models.Account.user_id == target_user_id).delete(synchronize_session=False)
    db.query(models.Category).filter(models.Category.user_id == target_user_id).delete(synchronize_session=False)
    db.delete(target_user)
    db.commit()
    return {"status": "ok", "message": f"Usuario #{target_user_id} ({target_user.email}) eliminado correctamente."}

def complete_onboarding(db: Session, user_id: int, data: schemas.OnboardingRequest):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user.monthly_income = data.monthly_income
    user.onboarding_completed = True

    if data.quick_buttons:
        user.quick_buttons_json = json.dumps(data.quick_buttons)

    if data.categories_budget:
        categories = get_categories(db, user_id)
        for cat in categories:
            if cat.name in data.categories_budget:
                cat.monthly_budget = float(data.categories_budget[cat.name])

    db.commit()
    db.refresh(user)
    return user

def update_user_quick_buttons(db: Session, user_id: int, buttons: list):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user.quick_buttons_json = json.dumps(buttons)
    db.commit()
    db.refresh(user)
    return user




# ==========================================
# FUNCIONES MULTI-TENANT (POR USER_ID)
# ==========================================
def get_accounts(db: Session, user_id: int):
    ensure_user_defaults(db, user_id)
    return db.query(models.Account).filter(models.Account.user_id == user_id).all()

def get_account_by_id(db: Session, account_id: int, user_id: int):
    return db.query(models.Account).filter(models.Account.id == account_id, models.Account.user_id == user_id).first()

def get_categories(db: Session, user_id: int):
    ensure_user_defaults(db, user_id)
    return db.query(models.Category).filter(models.Category.user_id == user_id).all()

def get_category_by_id(db: Session, category_id: int, user_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == user_id).first()


def record_expense(db: Session, expense: schemas.ExpenseCreate, user_id: int):
    account = get_account_by_id(db, expense.account_id, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta de origen no encontrada")

    if expense.category_id:
        category = get_category_by_id(db, expense.category_id, user_id)
        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    account.balance -= expense.amount

    db_tx = models.Transaction(
        user_id=user_id,
        amount=expense.amount,
        transaction_type="EXPENSE",
        account_id=expense.account_id,
        category_id=expense.category_id,
        note=expense.note
    )

    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    db.refresh(account)
    return db_tx


def record_transfer(db: Session, transfer: schemas.TransferCreate, user_id: int):
    if transfer.account_id == transfer.destination_account_id:
        raise HTTPException(status_code=400, detail="La cuenta de origen y destino no pueden ser iguales")

    source_account = get_account_by_id(db, transfer.account_id, user_id)
    if not source_account:
        raise HTTPException(status_code=404, detail="Cuenta de origen no encontrada")

    dest_account = get_account_by_id(db, transfer.destination_account_id, user_id)
    if not dest_account:
        raise HTTPException(status_code=404, detail="Cuenta de destino no encontrada")

    source_account.balance -= transfer.amount
    dest_account.balance += transfer.amount

    db_tx = models.Transaction(
        user_id=user_id,
        amount=transfer.amount,
        transaction_type="TRANSFER",
        account_id=transfer.account_id,
        destination_account_id=transfer.destination_account_id,
        note=transfer.note
    )

    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    db.refresh(source_account)
    db.refresh(dest_account)
    return db_tx


def record_income(db: Session, income: schemas.IncomeCreate, user_id: int):
    account = get_account_by_id(db, income.account_id, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    account.balance += income.amount

    db_tx = models.Transaction(
        user_id=user_id,
        amount=income.amount,
        transaction_type="INCOME",
        account_id=income.account_id,
        note=income.note
    )

    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


def delete_transaction(db: Session, transaction_id: int, user_id: int):
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    if tx.transaction_type == "EXPENSE":
        account = get_account_by_id(db, tx.account_id, user_id)
        if account:
            account.balance += tx.amount
    elif tx.transaction_type == "TRANSFER":
        source_account = get_account_by_id(db, tx.account_id, user_id)
        dest_account = get_account_by_id(db, tx.destination_account_id, user_id)
        if source_account:
            source_account.balance += tx.amount
        if dest_account:
            dest_account.balance -= tx.amount
    elif tx.transaction_type == "INCOME":
        account = get_account_by_id(db, tx.account_id, user_id)
        if account:
            account.balance -= tx.amount

    db.delete(tx)
    db.commit()
    return {"status": "ok", "message": f"Transacción #{transaction_id} eliminada y saldo revertido correctamente"}


def reset_database(db: Session, user_id: int):
    now = datetime.now()
    db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        extract("year", models.Transaction.date) == now.year,
        extract("month", models.Transaction.date) == now.month
    ).delete(synchronize_session=False)

    accounts = get_accounts(db, user_id)
    for acc in accounts:
        acc.balance = 0.0

    db.commit()
    return {"status": "ok", "message": "Saldos del mes reiniciados a $0. El historial de reportes mensuales pasados se mantiene intacto."}


def get_recent_transactions(db: Session, user_id: int, limit: int = 20):
    txs = db.query(models.Transaction).filter(models.Transaction.user_id == user_id).order_by(models.Transaction.date.desc()).limit(limit).all()
    result = []
    for tx in txs:
        tx_dict = {
            "id": tx.id,
            "amount": tx.amount,
            "transaction_type": tx.transaction_type,
            "account_id": tx.account_id,
            "account_name": tx.account.name if tx.account else None,
            "category_id": tx.category_id,
            "category_name": tx.category.name if tx.category else None,
            "destination_account_id": tx.destination_account_id,
            "destination_account_name": tx.destination_account.name if tx.destination_account else None,
            "date": tx.date,
            "note": tx.note,
        }
        result.append(tx_dict)
    return result


def get_dashboard_summary(db: Session, user_id: int):
    accounts = get_accounts(db, user_id)
    categories = get_categories(db, user_id)

    total_balance = sum(acc.balance for acc in accounts)

    now = datetime.now()
    current_year = now.year
    current_month = now.month

    _, total_days_in_month = calendar.monthrange(current_year, current_month)
    days_remaining = total_days_in_month - now.day + 1
    if days_remaining <= 0:
        days_remaining = 1

    categories_summary = []
    for cat in categories:
        spent_query = (
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
                models.Transaction.user_id == user_id,
                models.Transaction.category_id == cat.id,
                models.Transaction.transaction_type == "EXPENSE",
                extract("year", models.Transaction.date) == current_year,
                extract("month", models.Transaction.date) == current_month
            )
            .scalar()
        )
        total_spent = float(spent_query)
        percentage = (total_spent / cat.monthly_budget * 100) if cat.monthly_budget > 0 else 0.0

        categories_summary.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "monthly_budget": cat.monthly_budget,
            "total_spent": total_spent,
            "percentage_used": round(percentage, 1)
        })

    liquid_accounts = [acc for acc in accounts if acc.name in ["CuentaRUT", "Mercado Pago Disponible", "Efectivo (Billetera)"]]
    liquid_balance = sum(max(0.0, acc.balance) for acc in liquid_accounts)

    committed_expenses = 0.0
    for cat_item in categories_summary:
        name_lower = cat_item["category_name"].lower()
        if "arriendo" in name_lower or "fijo" in name_lower:
            pending = max(0.0, cat_item["monthly_budget"] - cat_item["total_spent"])
            committed_expenses += pending

    free_balance = max(0.0, liquid_balance - committed_expenses)
    daily_hormiga_limit = round(free_balance / days_remaining, 0)

    return {
        "total_balance": total_balance,
        "accounts": accounts,
        "categories_summary": categories_summary,
        "daily_hormiga_limit": daily_hormiga_limit,
        "days_remaining_in_month": days_remaining,
        "committed_expenses": committed_expenses,
        "free_balance": free_balance
    }


def get_monthly_report(db: Session, user_id: int, year: int, month: int):
    total_income = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.transaction_type == "INCOME",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month
        )
        .scalar()
    )
    total_income = float(total_income)

    total_expense = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.transaction_type == "EXPENSE",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month
        )
        .scalar()
    )
    total_expense = float(total_expense)

    net_savings = total_income - total_expense

    categories = get_categories(db, user_id)
    categories_breakdown = []
    for cat in categories:
        spent = (
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
                models.Transaction.user_id == user_id,
                models.Transaction.category_id == cat.id,
                models.Transaction.transaction_type == "EXPENSE",
                extract("year", models.Transaction.date) == year,
                extract("month", models.Transaction.date) == month
            )
            .scalar()
        )
        spent = float(spent)
        pct = (spent / cat.monthly_budget * 100) if cat.monthly_budget > 0 else 0.0
        categories_breakdown.append({
            "category_name": cat.name,
            "monthly_budget": cat.monthly_budget,
            "total_spent": spent,
            "percentage_used": round(pct, 1)
        })

    sorted_cats = sorted(categories_breakdown, key=lambda x: x["total_spent"], reverse=True)

    recommendations = []
    top_spent_cat = next((c for c in sorted_cats if c["total_spent"] > 0), None)
    if top_spent_cat:
        cat_name = top_spent_cat["category_name"]
        amt = top_spent_cat["total_spent"]
        if "Transporte" in cat_name:
            recommendations.append(
                f"🚕 Tu mayor gasto fue en '{cat_name}' (${amt:,.0f} CLP). Intenta planificar tus viajes con anticipación o combinar colectivos para reducir trayectos nocturnos en Uber."
            )
        elif "Alimentación" in cat_name:
            recommendations.append(
                f"🛒 Gastaste ${amt:,.0f} CLP en '{cat_name}'. Comprar en ferias locales o planificar compras semanales al por mayor puede ahorrarte hasta un 25% mensual."
            )
        elif "Ocio" in cat_name:
            recommendations.append(
                f"🎉 El gasto en '{cat_name}' alcanzó ${amt:,.0f} CLP. Fijar un límite estricto para salidas de fin de semana evitará imprevistos a fin de mes."
            )
        else:
            recommendations.append(
                f"💡 La categoría con mayor gasto fue '{cat_name}' (${amt:,.0f} CLP). Revisa si existen gastos hormiga secundarios en esta área."
            )

    if total_expense > total_income and total_income > 0:
        recommendations.append(
            "⚠️ Tus gastos superaron tus ingresos del mes. Considera agendar un evento DJ adicional o ajustar tus presupuestos en ocio y transporte."
        )
    elif net_savings > 0:
        recommendations.append(
            f"💪 ¡Excelente trabajo! Tuviste un superávit de ${net_savings:,.0f} CLP en este mes. Te aconsejamos mover parte de este saldo a 'Mercado Pago Ahorro' para proteger tu fondo del Máster."
        )

    overbudget_cats = [c for c in categories_breakdown if c["percentage_used"] > 100]
    if overbudget_cats:
        names = ", ".join([c["category_name"].split("(")[0].strip() for c in overbudget_cats])
        recommendations.append(
            f"🚨 Excediste el presupuesto asignado en: {names}. Intenta reajustar los límites para el próximo mes."
        )

    if not recommendations:
        recommendations.append("✨ Mantén el control de tus finanzas registrando todos tus ingresos y gastos diarios.")

    return {
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES.get(month, f"Mes {month}"),
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "categories_breakdown": sorted_cats,
        "recommendations": recommendations
    }
