import re

with open('alembic/env.py', 'r', encoding='utf-8') as f:
    env_py = f.read()

# I need to modify the config to read from os.getenv
setup_db_url = '''
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import models

# Set sqlalchemy.url dynamically
db_url = os.getenv("DATABASE_URL")
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", db_url)
else:
    # Fallback for local sqlite
    config.set_main_option("sqlalchemy.url", "sqlite:///finance.db")

target_metadata = models.Base.metadata
'''

# Find where config = context.config is, and put it after
env_py = re.sub(r'config = context\.config\n', 'config = context.config\n' + setup_db_url, env_py)
# Also remove my old manual import models block that I put in target_metadata earlier to avoid duplication
env_py = re.sub(r'import sys\nimport os\nsys\.path\.append.*?target_metadata = models\.Base\.metadata', '', env_py, flags=re.DOTALL)

with open('alembic/env.py', 'w', encoding='utf-8') as f:
    f.write(env_py)
