# 💰 Sistema de Gestión de Finanzas Personales Diario

Aplicación Web ligera y API RESTful en Python (FastAPI + SQLite + SQLAlchemy) para la administración del presupuesto mensual, seguimiento de cuentas y cálculo del límite diario de **gastos hormiga**.

---

## 🚀 Características Principales

1. **Gestión de Cuentas**:
   - **CuentaRUT**: Operativa diaria (colectivos, pasajes).
   - **Mercado Pago Disponible**: Reserva líquida (salidas, Ubers, refuerzo).
   - **Mercado Pago Ahorro**: Fondo protegido (Máster y emergencias).

2. **Categorización de Gastos**:
   - Presupuestos dinámicos para transporte, alimentación, ocio, deudas y ahorro.

3. **Cálculo Automático de Límite Diario Hormiga**:
   - Calcula cuánto dinero puedes gastar por día en antojos o gastos menores según el saldo líquido disponible y los días restantes del mes.

4. **Acciones Rápidas (1-Clic)**:
   - Registrar pasajes o ubers de forma instantánea sin escribir nada (*Colectivo Talca*, *Uber*, *Bus Linares*).

---

## 🛠️ Requisitos e Instalación

### 1. Requisitos Previos
Tener Python 3.9 o superior instalado.

### 2. Instalación de Dependencias
Abre una terminal en este directorio y ejecuta:

```bash
pip install -r requirements.txt
```

---

## 🏁 Ejecución de la Aplicación

Para iniciar el servidor de desarrollo local:

```bash
python app.py
```
o utilizando `uvicorn`:
```bash
uvicorn app:app --reload --port 8000
```

Luego abre tu navegador web en:
👉 **http://127.0.0.1:8000**

---

## 📋 Documentación de la API RESTful (Swagger UI)

FastAPI genera documentación interactiva automáticamente en:
👉 **http://127.0.0.1:8000/docs**

### Endpoints Principales:
- `POST /transactions/expense`: Registrar un gasto.
- `POST /transactions/transfer`: Mover saldo entre cuentas.
- `GET /dashboard`: Obtener saldos consolidados, gastos por categoría y límite diario hormiga.

---

## 🧪 Ejecutar Verificación de Pruebas

Para validar automáticamente la base de datos, el seed inicial y los cálculos de traspasos y gastos:

```bash
python verify.py
```
