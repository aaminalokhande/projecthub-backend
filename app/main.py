from fastapi import FastAPI

app = FastAPI(title="ProjectHub API")


@app.get("/")
def root():
    return {"message": "ProjectHub backend is running"}