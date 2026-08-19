import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.errors import register_exception_handlers
from common.logging import setup_logging
from common.middleware import RequestIdMiddleware
from config.settings import get_settings
from modules.alignment.router import router as alignment_router
from modules.analysis.router import router as analysis_router
from modules.audit.router import router as audit_router
from modules.auth.router import router as auth_router
from modules.council.router import router as council_router
from modules.decisions.router import router as decisions_router
from modules.demo.router import router as demo_router
from modules.documents.router import router as documents_router
from modules.documents.router import statements_router
from modules.executive.router import router as executive_router
from modules.identity.router import router as identity_router
from modules.ingestion.router import router as ingestion_router
from modules.knowledge.router import router as knowledge_router
from modules.kpi.router import router as kpi_router
from modules.outbox.router import router as outbox_router
from modules.pilot.router import router as pilot_router
from modules.quality.router import router as quality_router
from modules.resolution.router import router as resolution_router
from modules.rules.router import router as rules_router
from modules.system.router import router as system_router

setup_logging()
logger = logging.getLogger("business-os.startup")
settings = get_settings()

if settings.pilot_mode and settings.auth_required and settings.secrets_are_insecure():
    raise RuntimeError(
        "PILOT_MODE=true требует сменить AUTH_SECRET и WORKER_SECRET "
        "(не используйте значения по умолчанию)."
    )
if settings.auth_required and settings.secrets_are_insecure():
    logger.warning(
        "AUTH_REQUIRED=true, но AUTH_SECRET/WORKER_SECRET всё ещё дефолтные — "
        "смените перед shared pilot (или включите PILOT_MODE=true)."
    )

app = FastAPI(
    title="Business OS API",
    version="0.1.0",
    description="Business OS technical foundation API",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(identity_router)
app.include_router(audit_router)
app.include_router(documents_router)
app.include_router(statements_router)
app.include_router(ingestion_router)
app.include_router(quality_router)
app.include_router(resolution_router)
app.include_router(alignment_router)
app.include_router(rules_router)
app.include_router(knowledge_router)
app.include_router(kpi_router)
app.include_router(executive_router)
app.include_router(outbox_router)
app.include_router(analysis_router)
app.include_router(council_router)
app.include_router(decisions_router)
app.include_router(demo_router)
app.include_router(pilot_router)
