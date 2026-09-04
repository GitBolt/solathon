from typing import Any, NotRequired, TypedDict


class AccountInfoType(TypedDict):
    """
    JSON Response type of Account Information received by RPC
    """

    lamports: int
    owner: str
    executable: bool
    rentEpoch: int
    space: NotRequired[int]
    size: NotRequired[int]
    data: str | list[str] | dict[str, Any]


class AccountInfo:
    """
    Convert Account Information JSON to Class
    """

    def __init__(self, result: AccountInfoType) -> None:
        self.raw = result
        self.context: dict[str, Any] | None = None
        self.lamports = result["lamports"]
        self.owner = result["owner"]
        self.executable = result["executable"]
        self.rent_epoch = result["rentEpoch"]
        self.space = result.get("space", result.get("size"))
        self.size = self.space  # Backward-compatible alias.
        self.data = result["data"]

    def __repr__(self) -> str:
        return f"AccountInfo(owner={self.owner!r})"


class ProgramAccountType(TypedDict):
    """
    JSON Response type of Program Account Information received by RPC
    """

    pubkey: str
    account: AccountInfoType


class ProgramAccount:
    """
    Convert Program Account Information JSON to Class
    """

    def __init__(self, result: ProgramAccountType) -> None:
        self.raw = result
        self.pubkey = result["pubkey"]
        self.account = AccountInfo(result["account"])

    def __repr__(self) -> str:
        return f"ProgramAccount(pubkey={self.pubkey!r})"
