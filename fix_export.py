import re

with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

old_export = '''@app.get("/api/transactions/export")
def export_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):'''

new_export = '''@app.get("/api/transactions/export")
def export_transactions(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("user_id")
        current_user = crud.get_user_by_id(db, uid)
        if not current_user:
            raise HTTPException(status_code=401)
    except:
        raise HTTPException(status_code=401, detail="Token inválido")'''

app_py = app_py.replace(old_export, new_export)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)
    
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_link = '''<a href="/api/transactions/export" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200 hover:bg-emerald-100 transition-all">
                    <i class="fa-solid fa-file-excel"></i> Exportar a Excel
                </a>'''

new_link = '''<button onclick="downloadExport()" class="text-xs text-emerald-600 hover:text-emerald-700 font-bold flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200 hover:bg-emerald-100 transition-all">
                    <i class="fa-solid fa-file-excel"></i> Exportar a Excel
                </button>'''

html = html.replace(old_link, new_link)

js_func = '''
        function downloadExport() {
            if (authUserId) {
                window.location.href = `/api/transactions/export?token=${authUserId}`;
            } else {
                showToast("No estás autenticado");
            }
        }
        
        async function fetchDashboard() {'''
        
html = html.replace('        async function fetchDashboard() {', js_func)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
