import re

with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

# 1. Google Auth Fix
old_google = '''@app.post("/api/auth/google", response_model=schemas.TokenResponse)
def google_auth(google_data: schemas.GoogleAuth, db: Session = Depends(get_db)):
    """
    Recibe el ID Token JWT generado por Google Sign-In, extrae el correo y perfil, y autentica al usuario.
    """
    token = google_data.credential
    try:
        # Decodificar payload no firmado del JWT de Google
        parts = token.split(".")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Token de Google inválido")
        
        payload_b64 = parts[1]
        # Ajustar padding Base64 si es necesario
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.b64decode(payload_b64)
        data = json.loads(payload_bytes.decode('utf-8'))

        email = data.get("email")
        name = data.get("name") or email.split("@")[0]
        google_id = data.get("sub")
        picture = data.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="El token de Google no contiene un correo válido")

        # Buscar usuario por email o google_id
        user = crud.get_user_by_email(db, email)
        if not user:
            user = crud.create_user_with_defaults(
                db, name=name, email=email, google_id=google_id, picture=picture
            )
        else:
            if not user.google_id:
                user.google_id = google_id
            if picture:
                user.picture = picture
            db.commit()

        user = user or crud.get_user_by_email(db, email)
        
        return {
            "access_token": str(user.id),
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al verificar credenciales de Google: {str(e)}")'''

new_google = '''@app.post("/api/auth/google", response_model=schemas.TokenResponse)
def google_auth(google_data: schemas.GoogleAuth, db: Session = Depends(get_db)):
    """
    Recibe el ID Token JWT generado por Google Sign-In, verifica firma oficial y autentica.
    """
    token = google_data.credential
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado en el servidor.")
        
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        email = idinfo.get("email")
        name = idinfo.get("name") or email.split("@")[0]
        google_id = idinfo.get("sub")
        picture = idinfo.get("picture")

        if not email:
            raise HTTPException(status_code=401, detail="El token de Google no contiene un correo válido")

        user = crud.get_user_by_email(db, email)
        if not user:
            user = crud.create_user_with_defaults(
                db, name=name, email=email, google_id=google_id, picture=picture
            )
        else:
            if not user.google_id:
                user.google_id = google_id
            if picture:
                user.picture = picture
            db.commit()
            
        jwt_token = create_access_token({"user_id": user.id})
        return {
            "access_token": jwt_token,
            "user": user
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Token de Google inválido o expirado")
    except Exception as e:
        import logging
        logging.exception("Error al verificar credenciales de Google")
        raise HTTPException(status_code=500, detail="Error interno al verificar credenciales de Google")'''

app_py = app_py.replace(old_google, new_google)

# 2. Remove google-fast
fast_google_regex = r'@app\.post\("/api/auth/google-fast".*?return\s*\{[^}]*\}\s*'
app_py = re.sub(fast_google_regex, '', app_py, flags=re.DOTALL)

# 3. Protect reset-database
old_reset = '''@app.post("/api/reset-database")
def reset_database(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):'''

new_reset = '''@app.post("/api/reset-database")
def reset_database(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permisos insuficientes. Solo administradores pueden reiniciar la base de datos completa.")'''

app_py = app_py.replace(old_reset, new_reset)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)
