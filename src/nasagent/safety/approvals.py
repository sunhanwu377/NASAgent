from typing import Protocol


class ApprovalProvider(Protocol):
    def confirm(self, message: str) -> bool:
        raise NotImplementedError
