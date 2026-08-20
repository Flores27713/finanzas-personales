import re

with open('crud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add savings functions
savings_funcs = '''
# ==========================================
# METAS DE AHORRO
# ==========================================
def get_savings_goals(db: Session, user_id: int):
    return db.query(models.SavingsGoal).filter(models.SavingsGoal.user_id == user_id).all()

def create_savings_goal(db: Session, goal: schemas.SavingsGoalCreate, user_id: int):
    db_goal = models.SavingsGoal(
        user_id=user_id,
        name=goal.name,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        current_saved=0.0
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

def update_savings_goal(db: Session, goal_id: int, user_id: int, amount_to_add: float):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id, models.SavingsGoal.user_id == user_id).first()
    if goal:
        goal.current_saved += amount_to_add
        db.commit()
        db.refresh(goal)
    return goal

def delete_savings_goal(db: Session, goal_id: int, user_id: int):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id, models.SavingsGoal.user_id == user_id).first()
    if goal:
        db.delete(goal)
        db.commit()
        return True
    return False

def get_dashboard_summary('''

content = content.replace('def get_dashboard_summary(', savings_funcs)

# 2. Update get_dashboard_summary to calculate monthly savings commitment
old_dash_calc = '''    for cat_item in categories_summary:
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

new_dash_calc = '''    for cat_item in categories_summary:
        if cat_item.get("is_fixed", False):
            pending = max(0.0, cat_item["monthly_budget"] - cat_item["total_spent"])
            committed_expenses += pending

    # Add monthly savings commitment
    savings_goals = get_savings_goals(db, user_id)
    monthly_savings_commitment = 0.0
    for sg in savings_goals:
        remaining_amount = max(0.0, sg.target_amount - sg.current_saved)
        # Calculate months remaining
        from dateutil.relativedelta import relativedelta
        diff = relativedelta(sg.target_date, now.replace(tzinfo=timezone.utc) if sg.target_date.tzinfo else now)
        months_remaining = max(1, diff.years * 12 + diff.months)
        monthly_commitment = remaining_amount / months_remaining
        monthly_savings_commitment += monthly_commitment
    
    committed_expenses += monthly_savings_commitment

    free_balance = max(0.0, liquid_balance - committed_expenses)
    daily_hormiga_limit = round(free_balance / days_remaining, 0)

    return {
        "total_balance": total_balance,
        "accounts": accounts,
        "categories_summary": categories_summary,
        "savings_goals": savings_goals,
        "daily_hormiga_limit": daily_hormiga_limit,
        "days_remaining_in_month": days_remaining,
        "committed_expenses": committed_expenses,
        "free_balance": free_balance,
        "monthly_income": monthly_income,
        "credit_debt": credit_debt,
        "monthly_savings_commitment": monthly_savings_commitment
    }'''

content = content.replace(old_dash_calc, new_dash_calc)

# 3. Auto-categorization in create_expense
old_expense = '''def create_expense(db: Session, expense: schemas.ExpenseCreate, user_id: int):
    account = get_account_by_id(db, expense.account_id, user_id)
    if not account:
        raise ValueError("Cuenta no encontrada")
    
    if account.balance < expense.amount:
        if account.account_type != "Tarjeta de Crédito":
            raise ValueError("Saldo insuficiente en la cuenta")

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
    return db_tx'''

new_expense = '''def create_expense(db: Session, expense: schemas.ExpenseCreate, user_id: int):
    account = get_account_by_id(db, expense.account_id, user_id)
    if not account:
        raise ValueError("Cuenta no encontrada")
    
    if account.balance < expense.amount:
        if account.account_type != "Tarjeta de Crédito":
            raise ValueError("Saldo insuficiente en la cuenta")

    account.balance -= expense.amount
    
    # Auto-categorization if category is missing
    cat_id = expense.category_id
    if not cat_id and expense.note:
        similar_tx = db.query(models.Transaction).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.transaction_type == "EXPENSE",
            models.Transaction.category_id.isnot(None),
            models.Transaction.note.ilike(f"%{expense.note.strip()}%")
        ).order_by(models.Transaction.date.desc()).first()
        if similar_tx:
            cat_id = similar_tx.category_id

    db_tx = models.Transaction(
        user_id=user_id,
        amount=expense.amount,
        transaction_type="EXPENSE",
        account_id=expense.account_id,
        category_id=cat_id,
        note=expense.note
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx'''

content = content.replace(old_expense, new_expense)

with open('crud.py', 'w', encoding='utf-8') as f:
    f.write(content)
