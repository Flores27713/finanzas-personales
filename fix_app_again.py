import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add logging setup
logging_setup = '''import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

'''
if 'import logging' not in content:
    content = content.replace('import os\n', 'import os\n' + logging_setup)

# 2. Fix get_current_user
old_get_user = '''# Inyección de Dependencia para Identificar al Usuario Autenticado
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_str = auth_header.split(" ")[1]
        try:
            uid = int(token_str)
            u = crud.get_user_by_id(db, uid)
            if u:
                return u
        except ValueError:
            pass

    custom_uid = request.headers.get("x-app-user-id")
    if custom_uid:
        try:
            uid = int(custom_uid)
            u = crud.get_user_by_id(db, uid)
            if u:
                return u
        except ValueError:
            pass

    user_pin = request.headers.get("x-app-pin") or request.query_params.get("pin")
    if user_pin == APP_PIN:
        def_user = get_or_create_default_user(db)
        if def_user:
            return def_user

    raise HTTPException(status_code=401, detail="No autenticado")'''

new_get_user = '''# Inyección de Dependencia para Identificar al Usuario Autenticado
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token_str = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
            uid = payload.get("user_id")
            if uid is not None:
                u = crud.get_user_by_id(db, uid)
                if u:
                    return u
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Sesión expirada. Por favor inicia sesión nuevamente.")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Token inválido")

    raise HTTPException(status_code=401, detail="No autenticado")'''

if old_get_user in content:
    content = content.replace(old_get_user, new_get_user)
else:
    print("Could not find exact old_get_user match. Using regex.")
    content = re.sub(r'# Inyección de Dependencia para Identificar al Usuario Autenticado.*?raise HTTPException\(status_code=401, detail="No autenticado"\)', new_get_user, content, flags=re.DOTALL)

# 3. Clean up any remaining auto-migrations (if they exist)
auto_mig_regex = r'def run_auto_migrations\(\):.*?Base\.metadata\.create_all\(bind=engine\)'
content = re.sub(auto_mig_regex, '', content, flags=re.DOTALL)
content = content.replace('try:\n    run_auto_migrations()\nexcept Exception as e:\n    logger.error(f"[MIGRATION SETUP NOTICE] {e}")\n\nBase.metadata.create_all(bind=engine)', '')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
