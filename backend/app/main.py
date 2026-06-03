import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routes import auth, companies, assessments, regulatory

# Build SQL tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend API for credit risk evaluation, prompt engineering analysis, and regulatory RAG matching."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router Modules
app.include_router(auth.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(assessments.router, prefix="/api")
app.include_router(regulatory.router, prefix="/api")

# Serve Frontend static directory
static_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")

if os.path.exists(static_dir_path):
    app.mount("/static", StaticFiles(directory=static_dir_path), name="static")

# Catch-all endpoint to serve the static HTML Single Page Application
@app.get("/")
def read_root():
    index_path = os.path.join(static_dir_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API. Please open the Swagger UI at /docs or populate the static/ directory."
    }
