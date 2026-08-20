import re
with open('alembic/env.py', 'r', encoding='utf-8') as f:
    env_py = f.read()

new_target = '''import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import models
target_metadata = models.Base.metadata'''

env_py = env_py.replace('target_metadata = None', new_target)

with open('alembic/env.py', 'w', encoding='utf-8') as f:
    f.write(env_py)
