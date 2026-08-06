from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.errors import register_exception_handlers
from common.logging import setup_logging
from modules.system.router import router as system_router

setup_logging()

app = FastAPI(
    title="Business OS API",
    version="0.1.0",
    description="Business OS technical foundation API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(system_router)
