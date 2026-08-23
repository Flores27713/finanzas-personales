import re

# 1. Update app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

# Remove google_auth endpoint
google_auth_regex = r'@app\.post\("/api/auth/google", response_model=schemas\.TokenResponse\).*?def google_auth.*?except Exception as e:\n        logger\.exception\("Error al verificar credenciales de Google"\)\n        raise HTTPException\(status_code=401, detail="Error de autenticación con Google"\)'

app_py = re.sub(google_auth_regex, '', app_py, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)

# 2. Update index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove Google Sign-In script
html = re.sub(r'<script src="https://accounts\.google\.com/gsi/client" async defer></script>', '', html)

# Remove Google button UI
google_ui_regex = r'<!-- Botón Oficial de Google -->.*?<div class="g_id_signin" data-type="standard" data-shape="rectangular" data-theme="outline" data-text="signin_with" data-size="large" data-logo_alignment="left">\s*</div>'
html = re.sub(google_ui_regex, '', html, flags=re.DOTALL)

# Remove the handleCredentialResponse JS function
google_js_regex = r'async function handleCredentialResponse.*?\}'
html = re.sub(google_js_regex, '', html, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
