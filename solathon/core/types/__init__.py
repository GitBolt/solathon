from typing import Any, Generic, Literal, NotRequired, TypedDict, TypeVar

from .account_info import (
    AccountInfo,
    AccountInfoType,
    ProgramAccount,
    ProgramAccountType,
)
from .block import (
    Block,
    BlockCommitment,
    BlockCommitmentType,
    BlockHash,
    BlockHashType,
    BlockProduction,
    BlockProductionType,
    BlockType,
    TransactionElement,
    TransactionElementType,
)
from .cluster_node import ClusterNode, ClusterNodeType
from .epoch import Epoch, EpochSchedule, EpochScheduleType, EpochType
from .inflation import (
    InflationGovernor,
    InflationGovernorType,
    InflationRate,
    InflationRateType,
    InflationReward,
    InflationRewardType,
)

__all__ = [
    "AccountInfo",
    "AccountInfoType",
    "Block",
    "BlockCommitment",
    "BlockCommitmentType",
    "BlockHash",
    "BlockHashType",
    "BlockProduction",
    "BlockProductionType",
    "BlockType",
    "ClusterNode",
    "ClusterNodeType",
    "Commitment",
    "Context",
    "Epoch",
    "EpochSchedule",
    "EpochScheduleType",
    "EpochType",
    "InflationGovernor",
    "InflationGovernorType",
    "InflationRate",
    "InflationRateType",
    "InflationReward",
    "InflationRewardType",
    "LargestAccounts",
    "LargestAccountsType",
    "ProgramAccount",
    "ProgramAccountType",
    "PubKeyIdentity",
    "PubKeyIdentityType",
    "RPCError",
    "RPCErrorType",
    "RPCResponse",
    "RecentPerformanceSamples",
    "RecentPerformanceSamplesType",
    "Result",
    "SignatureStatus",
    "SignatureStatusType",
    "Supply",
    "SupplyType",
    "TransactionElement",
    "TransactionElementType",
    "TransactionSignature",
    "TransactionSignatureType",
]

T = TypeVar("T")


class RPCErrorType(TypedDict, total=False):
    """
    JSON Response type of RPC Error
    """

    code: int
    message: str
    data: Any


class RPCError:
    """
    Convert RPC Error JSON to Class
    """

    def __init__(self, error: RPCErrorType):
        self.raw = error
        self.code = error["code"]
        self.status_code = self.code
        self.message = error["message"]
        self.data = error.get("data")


class Context(TypedDict):
    slot: int
    apiVersion: NotRequired[str]


class Result(TypedDict, Generic[T]):
    context: Context
    value: T | None


class RPCResponse(TypedDict, Generic[T], total=False):
    jsonrpc: Literal["2.0"]
    id: int | str | None
    result: T
    error: RPCErrorType


Commitment = Literal["processed", "confirmed", "finalized"]


class PubKeyIdentityType(TypedDict):
    """
    JSON Response type of PubKey Identity received by RPC
    """

    identity: str


class PubKeyIdentity:
    """
    Convert PubKey Identity JSON to Class
    """

    def __init__(self, response: PubKeyIdentityType) -> None:
        self.raw = response
        self.identity = response["identity"]


class LargestAccountsType(TypedDict):
    """
    JSON Response type of Largest Accounts received by RPC
    """

    lamports: int
    address: str


class LargestAccounts:
    """
    Convert Largest Accounts JSON to Class
    """

    def __init__(self, response: LargestAccountsType) -> None:
        self.raw = response
        self.lamports = response["lamports"]
        self.address = response["address"]


class RecentPerformanceSamplesType(TypedDict):
    """
    JSON Response type of Recent Performance Samples received by RPC
    """

    slot: int
    numSlots: int
    numTransactions: int
    samplePeriodSecs: int
    numNonVoteTransactions: int


class RecentPerformanceSamples:
    """
    Convert Recent Performance Samples JSON to Class
    """

    def __init__(self, response: RecentPerformanceSamplesType) -> None:
        self.raw = response
        self.slot = response["slot"]
        self.num_slots = response["numSlots"]
        self.num_transactions = response["numTransactions"]
        self.sample_period_secs = response["samplePeriodSecs"]
        self.num_non_vote_transactions = response["numNonVoteTransactions"]


class TransactionSignatureType(TypedDict):
    """
    JSON Response type of Transaction Signature received by RPC
    """

    signature: str
    slot: int
    err: Any
    memo: str | None
    blockTime: int | None
    confirmationStatus: Commitment | None


class TransactionSignature:
    """
    Convert Transaction Signature JSON to Class
    """

    def __init__(self, response: TransactionSignatureType) -> None:
        self.raw = response
        self.signature = response["signature"]
        self.err = response.get("err")
        self.slot = response["slot"]
        self.memo = response.get("memo")
        self.block_time = response.get("blockTime")
        self.confirmation_status = response.get("confirmationStatus")


class SignatureStatusType(TypedDict):
    """
    JSON Response type of Signature Status received by RPC
    """

    slot: int
    confirmations: int | None
    err: Any
    confirmationStatus: Commitment | None


class SignatureStatus:
    """
    Convert Signature Status JSON to Class
    """

    def __init__(self, response: SignatureStatusType) -> None:
        self.raw = response
        self.slot = response["slot"]
        self.confirmations = response.get("confirmations")
        self.err = response.get("err")
        self.confirmation_status = response.get("confirmationStatus")


class SupplyType(TypedDict):
    """
    JSON Response type of Supply received by RPC
    """

    total: int
    circulating: int
    nonCirculating: int
    nonCirculatingAccounts: list[str]


class Supply:
    """
    Convert Supply JSON to Class
    """

    def __init__(self, response: SupplyType) -> None:
        self.raw = response
        self.context: Context | None = None
        self.total = response["total"]
        self.circulating = response["circulating"]
        self.non_circulating = response["nonCirculating"]
        self.non_circulating_accounts = response["nonCirculatingAccounts"]
