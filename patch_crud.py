import re

with open('crud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace password hashing logic
old_hash = '''import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256((password + "finanzas_secret_salt_2026").encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password'''

new_hash = '''import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password_fallback(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256((plain_password + "finanzas_secret_salt_2026").encode('utf-8')).hexdigest() == hashed_password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if it's a bcrypt hash
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            return pwd_context.verify(plain_password, hashed_password)
        else:
            return verify_password_fallback(plain_password, hashed_password)
    except Exception:
        return False'''

if old_hash in content:
    content = content.replace(old_hash, new_hash)
else:
    print("Old hash code not found exactly as expected. Using regex...")
    content = re.sub(r'import hashlib\s*def hash_password.*?verify_password\(.*?\).*?hashed_password', new_hash, content, flags=re.DOTALL)

# Update authenticate_user_email for silent migration
old_auth = '''def authenticate_user_email(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
    ensure_user_defaults(db, user.id)
    return user'''

new_auth = '''def authenticate_user_email(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
    
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
        
    # Migración silenciosa
    if not (user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")):
        user.hashed_password = hash_password(password)
        db.commit()

    ensure_user_defaults(db, user.id)
    return user'''

if old_auth in content:
    content = content.replace(old_auth, new_auth)
else:
    print("Old auth code not found exactly. Using replace on smaller chunks.")
    content = content.replace('    if not user.hashed_password or not verify_password(password, user.hashed_password):\n        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")',
                              '    if not user.hashed_password or not verify_password(password, user.hashed_password):\n        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")\n        \n    # Migración silenciosa\n    if not (user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")):\n        user.hashed_password = hash_password(password)\n        db.commit()')

with open('crud.py', 'w', encoding='utf-8') as f:
    f.write(content)
