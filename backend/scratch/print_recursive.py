import sys
from app.main import app

def print_routes():
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"{route.methods} {route.path}")
        if hasattr(route, "routes"):
            for subroute in route.routes:
                if hasattr(subroute, "path"):
                    print(f"  {subroute.methods} {subroute.path}")

print_routes()
