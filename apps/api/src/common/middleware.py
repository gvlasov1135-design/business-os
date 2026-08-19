import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from common.metrics import Timer, observe_request

logger = logging.getLogger("business-os.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        with Timer() as timer:
            response = await call_next(request)
        observe_request(
            method=request.method,
            status_code=response.status_code,
            duration_ms=timer.duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(timer.duration_ms, 2),
            },
        )
        return response
