import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix verify-pin
old_pin = '''@app.post("/api/verify-pin")
def check_pin(login: schemas.PinLogin, db: Session = Depends(get_db)):
    if login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    user = get_or_create_default_user(db)
    u_id = user.id if user else 1
    u_name = user.name if user else "Omar"
    return {"status": "ok", "message": "Acceso concedido", "user_id": u_id, "name": u_name}'''

new_pin = '''@app.post("/api/verify-pin")
@limiter.limit("5/minute")
def check_pin(request: Request, login: schemas.PinLogin, db: Session = Depends(get_db)):
    if not APP_PIN or login.pin != APP_PIN:
        raise HTTPException(status_code=401, detail="PIN de acceso incorrecto")
    user = get_or_create_default_user(db)
    token = create_access_token({"user_id": user.id})
    u_id = user.id if user else 1
    u_name = user.name if user else "Omar"
    return {"status": "ok", "message": "Acceso concedido", "user_id": u_id, "name": u_name, "access_token": token}'''
content = content.replace(old_pin, new_pin)

# Fix login
old_login = '''@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login_user(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user_email(db, email=login_data.email, password=login_data.password)
    return {
        "access_token": str(user.id),
        "token_type": "bearer",
        "user": user
    }'''

new_login = '''@app.post("/api/auth/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def login_user(request: Request, login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user_email(db, email=login_data.email, password=login_data.password)
    token = create_access_token({"user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }'''
content = content.replace(old_login, new_login)

# Fix register
old_reg = '''@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    if not user:
        user = crud.get_user_by_email(db, user_data.email)

    return {
        "access_token": str(user.id),
        "token_type": "bearer",
        "user": user
    }'''

new_reg = '''@app.post("/api/auth/register", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def register_user(request: Request, user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    user = crud.create_user_with_defaults(
        db, name=user_data.name, email=user_data.email, password=user_data.password
    )
    if not user:
        user = crud.get_user_by_email(db, user_data.email)

    token = create_access_token({"user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }'''
content = content.replace(old_reg, new_reg)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
