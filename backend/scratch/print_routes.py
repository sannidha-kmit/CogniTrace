import asyncio
from app.main import app

def print_routes():
    for route in app.routes:
        if hasattr(route, "path"):
            if "auto-generate" in route.path:
                print(f"{route.methods} {route.path}")

print_routes()
