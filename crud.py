import calendar
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException

import models
import schemas

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

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
    # Se consideran las cuentas operativas y líquidas: CuentaRUT, Mercado Pago Disponible y Efectivo (Billetera)
    liquid_accounts = [acc for acc in accounts if acc.name in ["CuentaRUT", "Mercado Pago Disponible", "Efectivo (Billetera)"]]
    liquid_balance = sum(max(0.0, acc.balance) for acc in liquid_accounts)


    daily_hormiga_limit = round(liquid_balance / days_remaining, 0)

    return {
        "total_balance": total_balance,
        "accounts": accounts,
        "categories_summary": categories_summary,
        "daily_hormiga_limit": daily_hormiga_limit,
        "days_remaining_in_month": days_remaining
    }


def get_monthly_report(db: Session, year: int, month: int):
    """
    Genera un reporte de cierre mensual con totales de ingresos, gastos, desglose y recomendaciones de ahorro.
    """
    # Total de Ingresos (INCOME) en el mes seleccionado
    total_income = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.transaction_type == "INCOME",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month
        )
        .scalar()
    )
    total_income = float(total_income)

    # Total de Gastos (EXPENSE) en el mes seleccionado
    total_expense = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.transaction_type == "EXPENSE",
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month
        )
        .scalar()
    )
    total_expense = float(total_expense)

    net_savings = total_income - total_expense

    # Desglose por categoría en ese mes
    categories = get_categories(db)
    categories_breakdown = []
    for cat in categories:
        spent = (
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
            .filter(
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

    # Recomendaciones Inteligentes de Ahorro
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
