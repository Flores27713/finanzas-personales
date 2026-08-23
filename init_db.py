import os
import sys
from sqlalchemy import create_engine, inspect
import alembic.config
import alembic.command

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set. Skipping DB init.")
        return

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Si la tabla 'users' existe pero 'alembic_version' NO existe,
    # significa que es una base de datos antigua que nunca usó Alembic.
    if "users" in tables and "alembic_version" not in tables:
        print("Migrando base de datos existente a Alembic...")
        # Estampamos la migración inicial (ad46b8d94add) para que no intente crear tablas que ya existen
        alembic.command.stamp(alembic_cfg, "ad46b8d94add")
        print("Stamp aplicado exitosamente.")
    
    print("Aplicando migraciones pendientes...")
    alembic.command.upgrade(alembic_cfg, "head")
    print("Migraciones aplicadas exitosamente.")

if __name__ == "__main__":
    main()
