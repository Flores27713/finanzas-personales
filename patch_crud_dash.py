import re

with open('crud.py', 'r', encoding='utf-8') as f:
    crud = f.read()

# 1. Update categories_summary.append to include is_fixed
old_append = '''        categories_summary.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "monthly_budget": cat.monthly_budget,
            "total_spent": total_spent,
            "percentage_used": round(percentage, 1)
        })'''

new_append = '''        categories_summary.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "monthly_budget": cat.monthly_budget,
            "total_spent": total_spent,
            "percentage_used": round(percentage, 1),
            "is_fixed": cat.is_fixed
        })'''
crud = crud.replace(old_append, new_append)

# 2. Replace liquid_accounts and committed_expenses
old_calc = '''    liquid_accounts = [acc for acc in accounts if acc.name in ["CuentaRUT", "Mercado Pago Disponible", "Efectivo (Billetera)"]]
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
    }'''

new_calc = '''    user = get_user_by_id(db, user_id)
    monthly_income = user.monthly_income if user else 0.0

    liquid_accounts = [acc for acc in accounts if acc.account_type != "Tarjeta de Crédito"]
    liquid_balance = sum(acc.balance for acc in liquid_accounts)

    credit_accounts = [acc for acc in accounts if acc.account_type == "Tarjeta de Crédito"]
    credit_debt = sum(acc.balance for acc in credit_accounts) # Balance on CC is usually represented negatively

    committed_expenses = 0.0
    for cat_item in categories_summary:
        if cat_item.get("is_fixed", False):
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
        "free_balance": free_balance,
        "monthly_income": monthly_income,
        "credit_debt": credit_debt
    }'''

crud = crud.replace(old_calc, new_calc)

with open('crud.py', 'w', encoding='utf-8') as f:
    f.write(crud)
