"""Protocol definition for the obs-gtwy gateway client."""

from typing import Protocol


class GatewayClientProtocol(Protocol):
    """Protocol for creating draft branches through obs-gtwy."""

    def create_draft_branch(
        self,
        *,
        file_name: str,
        content: str,
        branch_name: str,
    ) -> str:
        """Create a branch for the supplied draft and return its name."""
        ...
