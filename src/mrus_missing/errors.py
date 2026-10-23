"""Explicit bootstrap failure semantics."""


class StageNotImplemented(NotImplementedError):
    """A reserved production stage has not been delivered by its owner."""

    def __init__(self, stage: str, owner: str) -> None:
        self.stage = stage
        self.owner = owner
        super().__init__(f"{stage} is NOT_IMPLEMENTED; owner {owner}")


class BackendContractError(ValueError):
    """A backend returned output outside the shared contract; inputs may be valid."""
