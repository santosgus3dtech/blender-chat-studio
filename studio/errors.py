from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    code: str
    message: str
    retryable: bool = False
    status: int = 400

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}
