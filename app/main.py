from fastapi import FastAPI
from app.api.routes import router, auth_router
# from app.db import engine, Base
# from app.models.audit import AuditLog
app = FastAPI(title="AI Ops Email Agent")
@app.get("/")
def root():
    return {"status":"running"}
app.include_router(router)
app.include_router(auth_router)
