from fastapi import FastAPI
from app.database import Base, engine
from app.models import User, Project, Task
from app.routes.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ProjectHub API")


@app.get("/")
def root():
    return {"message": "ProjectHub backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ProjectHub API is healthy"}


app.include_router(auth_router)