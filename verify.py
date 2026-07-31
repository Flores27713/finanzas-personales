"""
Script de Verificación de Integridad y Lógica de Negocio
"""
import sys
from fastapi.testclient import TestClient
from app import app
from database import get_db, SessionLocal

client = TestClient(app)

def test_system():
    print("=== INICIANDO VERIFICACIÓN DE LA APLICACIÓN ===")
    
    # 0. Probar GET / (HTML Response)
    html_resp = client.get("/")
    assert html_resp.status_code == 200, f"Error en GET /: {html_resp.text}"
    print("[OK] Endpoint GET / (UI HTML) renderiza correctamente con código 200")

    # 1. Probar GET /dashboard
    response = client.get("/dashboard")
    assert response.status_code == 200, f"Error en /dashboard: {response.text}"
    data = response.json()
    
    print(f"[OK] Saldo Total Consolidado Inicial: ${data['total_balance']:,.0f} CLP")
    print(f"[OK] Límite Diario Gastos Hormiga: ${data['daily_hormiga_limit']:,.0f} CLP / día")
    print(f"[OK] Cuentas encontradas: {len(data['accounts'])}")
    print(f"[OK] Categorías encontradas: {len(data['categories_summary'])}")

    assert data['total_balance'] == 340000.0, f"Expected 340000, got {data['total_balance']}"
    assert len(data['accounts']) == 3
    assert len(data['categories_summary']) == 7

    # 2. Probar registrar un Gasto (Colectivo Talca -$1.000 de CuentaRUT)
    accounts = data['accounts']
    cuentarut = next(acc for acc in accounts if acc['name'] == 'CuentaRUT')
    cat_transporte = next(cat for cat in data['categories_summary'] if 'Transporte Talca' in cat['category_name'])

    expense_payload = {
        "amount": 1000.0,
        "account_id": cuentarut['id'],
        "category_id": cat_transporte['category_id'],
        "note": "Prueba Colectivo Talca"
    }

    resp_expense = client.post("/transactions/expense", json=expense_payload)
    assert resp_expense.status_code == 201, f"Error al registrar gasto: {resp_expense.text}"
    tx_exp = resp_expense.json()
    print(f"[OK] Gasto registrado correctamente: ID #{tx_exp['id']} - ${tx_exp['amount']} CLP")

    # 3. Probar Traspaso (Mover $15.000 de MP Disponible a CuentaRUT)
    mp_disponible = next(acc for acc in accounts if acc['name'] == 'Mercado Pago Disponible')
    
    transfer_payload = {
        "amount": 15000.0,
        "account_id": mp_disponible['id'],
        "destination_account_id": cuentarut['id'],
        "note": "Prueba Traspaso"
    }

    resp_transfer = client.post("/transactions/transfer", json=transfer_payload)
    assert resp_transfer.status_code == 201, f"Error al realizar traspaso: {resp_transfer.text}"
    tx_trans = resp_transfer.json()
    print(f"[OK] Traspaso registrado correctamente: ID #{tx_trans['id']} - ${tx_trans['amount']} CLP")

    # 4. Verificar saldos actualizados en Dashboard
    resp_dash2 = client.get("/dashboard")
    data2 = resp_dash2.json()
    accs2 = {acc['name']: acc['balance'] for acc in data2['accounts']}
    
    print("=== SALDOS TRAS OPERACIONES ===")
    for name, bal in accs2.items():
        print(f"  - {name}: ${bal:,.0f} CLP")
    
    # Saldo original CuentaRUT: 120.000 - 1.000 (gasto) + 15.000 (traspaso) = 134.000
    assert accs2['CuentaRUT'] == 134000.0, f"Expected 134000, got {accs2['CuentaRUT']}"
    # Saldo original MP Disponible: 70.000 - 15.000 (traspaso) = 55.000
    assert accs2['Mercado Pago Disponible'] == 55000.0, f"Expected 55000, got {accs2['Mercado Pago Disponible']}"
    # Saldo original MP Ahorro: 150.000
    assert accs2['Mercado Pago Ahorro'] == 150000.0

    print("--- TODAS LAS PRUEBAS DE INTEGRIDAD PASARON CON EXITO ---")


if __name__ == "__main__":
    test_system()
