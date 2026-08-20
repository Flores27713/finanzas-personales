import os

with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

imports_to_add = '''import jwt
from datetime import datetime, timedelta, timezone
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
'''

# insert after import os
app_py = app_py.replace('import os\n', 'import os\n' + imports_to_add)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_py)
