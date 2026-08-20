import re

with open('schemas.py', 'r', encoding='utf-8') as f:
    content = f.read()

savings_schemas = '''
class SavingsGoalCreate(BaseModel):
    name: str = Field(..., description="Nombre de la meta de ahorro")
    target_amount: float = Field(..., gt=0, description="Monto objetivo a ahorrar")
    target_date: datetime = Field(..., description="Fecha límite para cumplir la meta")

class SavingsGoalResponse(BaseModel):
    id: int
    name: str
    target_amount: float
    current_saved: float
    target_date: datetime
    
    model_config = ConfigDict(from_attributes=True)

class DashboardSummary(BaseModel):'''

content = content.replace('class DashboardSummary(BaseModel):', savings_schemas)

with open('schemas.py', 'w', encoding='utf-8') as f:
    f.write(content)
