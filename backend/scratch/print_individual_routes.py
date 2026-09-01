import sys
from app.api.v1.health import router as health_router

print("Health Router routes:")
for route in health_router.routes:
    print(route.path)

from app.api.v1.questions import router as questions_router
print("Questions Router routes:")
for route in questions_router.routes:
    print(route.path)
