from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.models import router as models_router
from app.api.routes.validation import router as validation_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.regulatory import router as regulatory_router
from app.api.routes.audit import router as audit_router
from app.api.routes import realtime   # ✅ ONLY THIS (no ws_router)
from app.api.routes import jira_dummy

from app.core.database import init_db

# ✅ Register models
from app.models.inventory import ModelInventory, ModelMetricsHistory
from app.models.audit_log import AuditLog
from app.models.validation import ValidationRecord


app = FastAPI()

# ✅ FIXED CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ✅ clean
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ROUTES
app.include_router(onboarding_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(regulatory_router, prefix="/api")
app.include_router(audit_router, prefix="/api")

# ✅ ✅ IMPORTANT: WebSocket router
app.include_router(realtime.router)   # ✅ correct

# ✅ Jira routes
app.include_router(jira_dummy.router, prefix="/api")

# ✅ HEALTH
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "compliance": "SR 11-7 ready"
    }

# ✅ STARTUP
@app.on_event("startup")
async def startup():
    print("✅ Creating DB tables...")
    await init_db()
    print("✅ Done")
