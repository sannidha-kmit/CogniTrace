from fastapi import APIRouter, FastAPI

health_router = APIRouter()
@health_router.get("/health")
def h(): pass

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])

app = FastAPI()
app.include_router(api_router, prefix="/api/v1")

print("API Router routes:")
for r in api_router.routes:
    print(r.path)

print("App routes:")
for r in app.routes:
    print(r.path)
