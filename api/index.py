import os
import sys
from pathlib import Path

# Add project root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Mark environment as Vercel serverless
os.environ["VERCEL"] = "1"

from app import create_app

# WSGI callable entrypoint expected by Vercel @vercel/python
app = create_app("production")
