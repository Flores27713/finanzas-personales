import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add exports endpoint and savings endpoints
new_endpoints = '''
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@app.get("/api/transactions/export")
def export_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    txs = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).order_by(models.Transaction.date.desc()).all()
    
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["ID", "Fecha", "Tipo", "Monto", "Cuenta Origen", "Cuenta Destino", "Categoria", "Nota"])
    
    for tx in txs:
        cat_name = tx.category.name if tx.category else ""
        acc_name = tx.account.name if tx.account else ""
        dest_name = tx.destination_account.name if tx.destination_account else ""
        date_str = tx.date.strftime("%Y-%m-%d %H:%M")
        writer.writerow([tx.id, date_str, tx.transaction_type, tx.amount, acc_name, dest_name, cat_name, tx.note or ""])
        
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=historial_transacciones.csv"
    return response

@app.post("/api/savings", response_model=schemas.SavingsGoalResponse)
def create_savings_goal(goal: schemas.SavingsGoalCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_savings_goal(db, goal, current_user.id)

@app.delete("/api/savings/{goal_id}")
def delete_savings_goal(goal_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if crud.delete_savings_goal(db, goal_id, current_user.id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Meta de ahorro no encontrada")
'''

content = content.replace('# ==========================================\n# ENDPOINTS DE ADMINISTRACIÓN', new_endpoints + '\n# ==========================================\n# ENDPOINTS DE ADMINISTRACIÓN')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
