import calendar
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException

import models
import schemas

def get_accounts(db: Session):
    return db.query(models.Account).all()

def get_account_by_id(db: Session, account_id: int):
    return db.query(models.Account).filter(models.Account.id == account_id).first()

def get_categories(db: Session):
    return db.query(models.Category).all()

def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def record_expense(db: Session, expense: schemas.ExpenseCreate):
    account = get_account_by_id(db, expense.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta de origen no encontrada")

    if expense.category_id:
        category = get_category_by_id(db, expense.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Actualizar saldo de la cuenta de origen
    account.balance -= expense.amount

    # Crear la transacción
    db_tx = models.Transaction(
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


def record_transfer(db: Session, transfer: schemas.TransferCreate):
    if transfer.account_id == transfer.destination_account_id:
        raise HTTPException(status_code=400, detail="La cuenta de origen y destino no pueden ser iguales")

    source_account = get_account_by_id(db, transfer.account_id)
    if not source_account:
        raise HTTPException(status_code=404, detail="Cuenta de origen no encontrada")

    dest_account = get_account_by_id(db, transfer.destination_account_id)
    if not dest_account:
        raise HTTPException(status_code=404, detail="Cuenta de destino no encontrada")

    # Modificar saldos
    source_account.balance -= transfer.amount
    dest_account.balance += transfer.amount

    # Crear la transacción
    db_tx = models.Transaction(
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


def record_income(db: Session, income: schemas.IncomeCreate):
    account = get_account_by_id(db, income.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    account.balance += income.amount

    db_tx = models.Transaction(
        amount=income.amount,
        transaction_type="INCOME",
        account_id=income.account_id,
        note=income.note
    )

    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


def delete_transaction(db: Session, transaction_id: int):
    """
    Elimina una transacción por su ID y revierte automáticamente los saldos en las cuentas correspondientes.
    """
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    # Revertir saldos según el tipo de transacción
    if tx.transaction_type == "EXPENSE":
        account = get_account_by_id(db, tx.account_id)
        if account:
            account.balance += tx.amount
    elif tx.transaction_type == "TRANSFER":
        source_account = get_account_by_id(db, tx.account_id)
        dest_account = get_account_by_id(db, tx.destination_account_id)
        if source_account:
            source_account.balance += tx.amount
        if dest_account:
            dest_account.balance -= tx.amount
    elif tx.transaction_type == "INCOME":
        account = get_account_by_id(db, tx.account_id)
        if account:
            account.balance -= tx.amount

    db.delete(tx)
    db.commit()
    return {"status": "ok", "message": f"Transacción #{transaction_id} eliminada y saldo revertido correctamente"}


def get_recent_transactions(db: Session, limit: int = 20):
    txs = db.query(models.Transaction).order_by(models.Transaction.date.desc()).limit(limit).all()
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


def get_dashboard_summary(db: Session):
    accounts = get_accounts(db)
    categories = get_categories(db)

    # 1. Saldo consolidado total
    total_balance = sum(acc.balance for acc in accounts)

    # 2. Gastos por categoría en el mes actual
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # Calcular días restantes en el mes
    _, total_days_in_month = calendar.monthrange(current_year, current_month)
    days_remaining = total_days_in_month - now.day + 1
    if days_remaining <= 0:
        days_remaining = 1

    categories_summary = []
    for cat in categories:
        # Sumar transacciones de tipo EXPENSE para esta categoría en el mes actual
        spent_query = (
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
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

    # 3. Límite diario disponible para gastos hormiga
    # Se consideran las cuentas operativas y líquidas: CuentaRUT y Mercado Pago Disponible
    liquid_accounts = [acc for acc in accounts if acc.name in ["CuentaRUT", "Mercado Pago Disponible"]]
    liquid_balance = sum(max(0.0, acc.balance) for acc in liquid_accounts)

    daily_hormiga_limit = round(liquid_balance / days_remaining, 0)

    return {
        "total_balance": total_balance,
        "accounts": accounts,
        "categories_summary": categories_summary,
        "daily_hormiga_limit": daily_hormiga_limit,
        "days_remaining_in_month": days_remaining
    }
