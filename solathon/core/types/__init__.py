from .account_info import AccountInfo, AccountInfoType, ProgramAccount, ProgramAccountType
from .block import Block, BlockType, BlockProduction, BlockProductionType, BlockCommitment, BlockCommitmentType, BlockHash, BlockHashType, TransactionElement, TransactionElementType
from .cluster_node import ClusterNode, ClusterNodeType
from .epoch import Epoch, EpochType, EpochSchedule, EpochScheduleType
from .inflation import InflationGovernor, InflationGovernorType, InflationRate, InflationRateType, InflationReward, InflationRewardType
from typing import List, Optional, TypeVar, TypedDict, Literal, Any, Union

T = TypeVar('T')

class RPCErrorType(TypedDict):
    '''
    JSON Response type of RPC Error
    '''
    status_code: int
    message: str

class RPCError():
    '''
    Convert RPC Error JSON to Class
    '''

    def __init__(self, error: RPCErrorType):
        self.status_code = error['status_code']
        self.message = error['message']


class Context(TypedDict):
    slot: int
    apiVersion: int

class Result(TypedDict):
    context: Context
    value: Union[T, None]

class RPCResponse(TypedDict):
    jsonrpc: Literal["2.0"]
    id: int
    result: Any
    error: RPCErrorType

Commitment = Literal["processed", "confirmed", "finalized", "recent", "single", "singleGossip", "root", "max"]
CommitmentConfig = Literal["processed", "confirmed", "finalized"]

class PubKeyIdentityType(TypedDict):
    '''
    JSON Response type of PubKey Identity received by RPC
    '''
    identity: str

class PubKeyIdentity:
    '''
    Convert PubKey Identity JSON to Class
    '''

    def __init__(self, response: PubKeyIdentityType) -> None:
        self.identity = response['identity']

class LargestAccountsType(TypedDict):
    '''
    JSON Response type of Largest Accounts received by RPC
    '''
    lamports: int
    address: str

class LargestAccounts:
    '''
    Convert Largest Accounts JSON to Class
    '''
    def __init__(self, response: LargestAccountsType) -> None:
        self.lamports = response['lamports']
        self.address = response['address']
        
class LargestTokenAccountsType(TypedDict):
    '''
    JSON Response type of Largest Token Accounts received by RPC
    '''
    address: set
    amount: int
    decimals: int
    uiAmount: float
    uiAmountString: str

class LargestTokenAccounts:
    '''
    Convert Largest Token Accounts JSON to Class
    '''
    def __init__(self, response: LargestTokenAccountsType) -> None:
        self.address = response['address']
        self.amount = response['amount']
        self.decimals = response['decimals']
        self.uiAmount = response['uiAmount']
        self.uiAmountString = response['uiAmountString']

class RecentPerformanceSamplesType(TypedDict):
    '''
    JSON Response type of Recent Performance Samples received by RPC
    '''
    slot: int
    numSlots: int
    numTransactions: int
    samplePeriodSecs: int
    numNonVoteTransaction: int

class RecentPerformanceSamples:
    '''
    Convert Recent Performance Samples JSON to Class
    '''
    def __init__(self, response: RecentPerformanceSamplesType) -> None:
        self.slot = response['slot']
        self.num_slots = response['numSlots']
        self.num_transactions = response['numTransactions']
        self.sample_period_secs = response['samplePeriodSecs']
        self.num_non_vote_transaction = response['numNonVoteTransaction']

class TransactionSignatureType(TypedDict):
    '''
    JSON Response type of Transaction Signature received by RPC
    '''
    signature: str
    slot: int
    err: Any
    memo: Optional[str]
    blockTime: Optional[int]
    confirmationStatus: Optional[CommitmentConfig]

class TransactionSignature:
    '''
    Convert Transaction Signature JSON to Class
    '''

    def __init__(self, response: TransactionSignatureType) -> None:
        self.signature = response['signature']
        self.err = response['err']
        self.slot = response['slot']
        self.memo = response['memo']
        self.block_time = response['blockTime']
        self.confirmation_status = response['confirmationStatus']

class SignatureStatusType(TypedDict):
    '''
    JSON Response type of Signature Status received by RPC
    '''
    slot: int
    confirmations: Optional[int]
    err: Any
    confirmationStatus: Optional[CommitmentConfig]

class SignatureStatus:
    '''
    Convert Signature Status JSON to Class
    '''

    def __init__(self, response: SignatureStatusType) -> None:
        self.slot = response['slot']
        self.confirmations = response['confirmations']
        self.err = response['err']
        self.confirmation_status = response['confirmationStatus']

class SupplyType(TypedDict):
    '''
    JSON Response type of Supply received by RPC
    '''
    total: int
    circulating: int
    nonCirculating: int
    nonCirculatingAccounts: List[str]

class Supply:
    '''
    Convert Supply JSON to Class
    '''

    def __init__(self, response: SupplyType) -> None:
        self.total = response['total']
        self.circulating = response['circulating']
        self.non_circulating = response['nonCirculating']
        self.non_circulating_accounts = response['nonCirculatingAccounts']