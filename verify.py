import os
from database import engine

engine.dispose()
if os.path.exists("finance.db"):
    try:
        os.remove("finance.db")
    except Exception:
        pass

from fastapi.testclient import TestClient
from app import app, APP_PIN

client = TestClient(app)






def test_system():
    print("=== INICIANDO VERIFICACIÓN DE LA APLICACIÓN ===")
    
    # 0. Probar GET / (HTML Response)
    html_resp = client.get("/")
    assert html_resp.status_code == 200, f"Error en GET /: {html_resp.text}"
    print("[OK] Endpoint GET / (UI HTML) renderiza correctamente con código 200")

    # 1. Probar acceso denegado sin PIN (401 Unauthorized)
    unauth_resp = client.get("/dashboard")
    assert unauth_resp.status_code == 401, "Se esperaba 401 sin PIN"
    print("[OK] Acceso bloqueado sin PIN (HTTP 401)")

    # 2. Probar vericacićn de PIN
    pin_resp = client.post("/api/verify-pin", json={"pin": APP_PIN})
    assert pin_resp.status_code == 200
    print(f"[OK] PIN '{APP_PIN}' verificado correctamente")

    headers = {"x-app-pin": APP_PIN}

    # 3. Probar GET /dashboard con PIN
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200, f"Error en /dashboard: {response.text}"
    data = response.json()
    
    print(f"[OK] Saldo Total Consolidado Inicial: ${data['total_balance']:,.0f} CLP")
    print(f"[OK] Límite Diario Gastos Hormiga: ${data['daily_hormiga_limit']:,.0f} CLP / día")
    print(f"[OK] Cuentas encontradas: {len(data['accounts'])}")
    print(f"[OK] Categorías encontradas: {len(data['categories_summary'])}")

    assert data['total_balance'] == 0.0, f"Expected 0.0, got {data['total_balance']}"
    assert len(data['accounts']) == 4
    assert len(data['categories_summary']) == 6

    # 4. Probar registrar un Gasto (Colectivo Talca -$1.000 de CuentaRUT)
    accounts = data['accounts']
    cuentarut = next(acc for acc in accounts if acc['name'] == 'CuentaRUT')
    cat_transporte = next(cat for cat in data['categories_summary'] if 'Transporte' in cat['category_name'])


    expense_payload = {
        "amount": 1000.0,
        "account_id": cuentarut['id'],
        "category_id": cat_transporte['category_id'],
        "note": "Prueba Colectivo Talca"
    }

    resp_exp = client.post("/transactions/expense", json=expense_payload, headers=headers)
    assert resp_exp.status_code == 201, f"Error al registrar gasto: {resp_exp.text}"
    tx_exp = resp_exp.json()
    print(f"[OK] Gasto registrado correctamente: ID #{tx_exp['id']} - ${tx_exp['amount']} CLP")

    # 5. Probar Traspaso entre Cuentas ($15.000 de MP Disponible a CuentaRUT)
    mp_disponible = next(acc for acc in accounts if acc['name'] == 'Mercado Pago Disponible')
    
    transfer_payload = {
        "amount": 15000.0,
        "account_id": mp_disponible['id'],
        "destination_account_id": cuentarut['id'],
        "note": "Prueba Traspaso"
    }

    resp_transfer = client.post("/transactions/transfer", json=transfer_payload, headers=headers)
    assert resp_transfer.status_code == 201, f"Error al realizar traspaso: {resp_transfer.text}"
    tx_trans = resp_transfer.json()
    print(f"[OK] Traspaso registrado correctamente: ID #{tx_trans['id']} - ${tx_trans['amount']} CLP")

    # 5.5 Probar Ingreso DJ (+50.000 a MP Disponible)
    income_payload = {
        "amount": 50000.0,
        "account_id": mp_disponible['id'],
        "note": "Evento DJ Matrimonio"
    }

    resp_income = client.post("/transactions/income", json=income_payload, headers=headers)
    assert resp_income.status_code == 201, f"Error al registrar ingreso: {resp_income.text}"
    tx_inc = resp_income.json()
    print(f"[OK] Ingreso DJ registrado correctamente: ID #{tx_inc['id']} - +${tx_inc['amount']} CLP")

    # 6. Verificar saldos actualizados en Dashboard
    resp_dash2 = client.get("/dashboard", headers=headers)

    data2 = resp_dash2.json()
    accs2 = {acc['name']: acc['balance'] for acc in data2['accounts']}
    
    print("=== SALDOS TRAS OPERACIONES ===")
    for name, bal in accs2.items():
        print(f"  - {name}: ${bal:,.0f} CLP")
    
    assert accs2['CuentaRUT'] == 14000.0, f"Expected 14000, got {accs2['CuentaRUT']}"
    assert accs2['Mercado Pago Disponible'] == 35000.0, f"Expected 35000, got {accs2['Mercado Pago Disponible']}"

    # 7. Probar eliminación de transacción y reversión de saldo
    del_resp = client.delete(f"/transactions/{tx_exp['id']}", headers=headers)
    assert del_resp.status_code == 200, f"Error al eliminar transacción: {del_resp.text}"
    print(f"[OK] Transacción #{tx_exp['id']} eliminada correctamente")

    resp_dash3 = client.get("/dashboard", headers=headers)
    accs3 = {acc['name']: acc['balance'] for acc in resp_dash3.json()['accounts']}
    assert accs3['CuentaRUT'] == 15000.0, f"Expected 15000 after delete, got {accs3['CuentaRUT']}"

    # 8. Probar Reporte de Cierre Mensual
    rep_resp = client.get("/api/monthly-report", headers=headers)
    assert rep_resp.status_code == 200, f"Error en reporte mensual: {rep_resp.text}"
    rep_data = rep_resp.json()
    assert "recommendations" in rep_data
    print(f"[OK] Reporte Mensual ({rep_data['month_name']} {rep_data['year']}) obtenido con {len(rep_data['recommendations'])} recomendaciones")

    # 9. Probar Registro de Usuario Nuevo y Aislamiento Multi-Tenant
    reg_resp = client.post("/api/auth/register", json={
        "name": "Prueba Usuario B",
        "email": "usuarioB@test.com",
        "password": "password123"
    })
    assert reg_resp.status_code == 200, f"Error al registrar usuario: {reg_resp.text}"
    userB_data = reg_resp.json()
    tokenB = userB_data["access_token"]
    headersB = {"Authorization": f"Bearer {tokenB}"}

    dashB = client.get("/dashboard", headers=headersB).json()
    assert dashB["total_balance"] == 0.0, "El nuevo usuario debe comenzar en $0"


    assert len(dashB["accounts"]) == 4, "El nuevo usuario debe tener sus 4 cuentas por defecto"
    print(f"[OK] Registro de Usuario B completado. Espacio aislado en $0 con {len(dashB['accounts'])} cuentas.")

    print("--- TODAS LAS PRUEBAS DE SEGURIDAD E INTEGRIDAD PASARON CON EXITO ---")


if __name__ == "__main__":
    test_system()

