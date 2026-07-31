import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Obtener la URL de la base de datos desde las Variables de Entorno de Render (PostgreSQL)
# Si no existe (en tu PC local), utilizará SQLite como respaldo automáticamente.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render en ocasiones entrega la URL con 'postgres://', pero SQLAlchemy 2.0 requiere 'postgresql://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Mantiene activas las conexiones en la nube
        pool_size=10,
        max_overflow=20
    )
else:
    # Respaldo para desarrollo local en SQLite
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "finance.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

# Fábrica de sesiones de SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase Base para los Modelos ORM
Base = declarative_base()

# Helper de inyección de dependencia de sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
