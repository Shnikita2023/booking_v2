"""Application error types and FastAPI error handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        detail: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.detail = detail
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: list[dict[str, Any]] = [
            {"loc": [str(loc) for loc in err["loc"]], "msg": err["msg"]} for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": errors, "code": "validation_error"},
        )
