import sys
from app.api.v1 import api_router
from app.main import app

print("API Router routes:")
for route in api_router.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")

print("App routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")
