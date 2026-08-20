import re

with open('schemas.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add to DashboardSummary
old_dash = '''class DashboardSummary(BaseModel):
    total_balance: float
    accounts: List[AccountResponse]
    categories_summary: List[CategorySpent]
    daily_hormiga_limit: float
    days_remaining_in_month: int
    committed_expenses: float = 0.0
    free_balance: float = 0.0
    monthly_income: float = 0.0
    credit_debt: float = 0.0'''

new_dash = '''class DashboardSummary(BaseModel):
    total_balance: float
    accounts: List[AccountResponse]
    categories_summary: List[CategorySpent]
    savings_goals: List[SavingsGoalResponse] = Field(default_factory=list)
    daily_hormiga_limit: float
    days_remaining_in_month: int
    committed_expenses: float = 0.0
    free_balance: float = 0.0
    monthly_income: float = 0.0
    credit_debt: float = 0.0
    monthly_savings_commitment: float = 0.0'''

content = content.replace(old_dash, new_dash)

with open('schemas.py', 'w', encoding='utf-8') as f:
    f.write(content)
