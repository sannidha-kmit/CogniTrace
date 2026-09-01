import sys
from app.main import app

for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")
