class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundException(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} with id '{resource_id}' not found",
            status_code=404,
        )


class ValidationException(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)
