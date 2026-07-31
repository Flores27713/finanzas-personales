import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Ruta a la base de datos SQLite en la misma carpeta del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "finance.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Configuración del Motor de SQLAlchemy (check_same_thread=False es necesario para SQLite con FastAPI)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fábrica de sesiones
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
