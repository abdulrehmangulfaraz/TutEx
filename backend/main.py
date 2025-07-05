from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from .routers import auth, dashboard, api
from .database import SessionLocal
from .config import config  # Assuming python-decouple
from fastapi.middleware import Middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

app = FastAPI()
templates = Jinja2Templates(directory="../frontend/templates")

limiter = Limiter(key_func=get_remote_address)
middleware = [Middleware(limiter)]
app = FastAPI(middleware=middleware)  # Use this single instance

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(api.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)