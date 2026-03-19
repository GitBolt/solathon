from solathon.core.message import Message as CoreMessage, MessageHeader
from typing import Any, List, TypedDict, Union, Dict


class HeaderType(TypedDict):
    '''
    JSON Response type of Header Information received by RPC
    '''
    numReadonlySignedAccounts: int
    numReadonlyUnsignedAccounts: int
    numRequiredSignatures: int


class Header:

    def __init__(self, response: HeaderType) -> None:
        self.num_readonly_signed_accounts = response['numReadonlySignedAccounts']
        self.num_readonly_unsigned_accounts = response['numReadonlyUnsignedAccounts']
        self.num_required_signatures = response['numRequiredSignatures']

    def __repr__(self) -> str:
        return f"Header(num_required_signatures={self.num_required_signatures!r}, num_readonly_signed_accounts={self.num_readonly_signed_accounts!r}, num_readonly_unsigned_accounts={self.num_readonly_unsigned_accounts!r})"


class InstructionType(TypedDict):
    '''
    JSON Response type of Instruction Information received by RPC
    '''
    accounts: List[int]
    data: str
    programIdIndex: int


class Instruction:
    '''
    Convert Instruction JSON to Class
    '''

    def __init__(self, response: InstructionType) -> None:
        self.accounts = response['accounts']
        self.data = response['data']
        self.program_id_index = response['programIdIndex']

    def __repr__(self) -> str:
        return f"Instruction(num_accounts={len(self.accounts)!r}, program_id_index={self.program_id_index!r})"


class MessageType(TypedDict):
    '''
    JSON Response type of Message Information received by RPC
    '''
    accountKeys: List[str]
    header: HeaderType
    instructions: List[InstructionType]
    recentBlockhash: str


class Message:
    '''
    Convert Message JSON to Class
    '''

    def __init__(self, response: MessageType) -> None:
        self.account_keys = response['accountKeys']
        header = Header(response['header'])
        self.header = MessageHeader(
            num_required_signatures=header.num_required_signatures,
            num_readonly_signed_accounts=header.num_readonly_signed_accounts,
            num_readonly_unsigned_accounts=header.num_readonly_unsigned_accounts
        )
        self.instructions = [Instruction(instruction)
                             for instruction in response['instructions']]
        self.recent_blockhash = response['recentBlockhash']

    def __repr__(self) -> str:
        return f"Message(header={self.header!r}, num_instructions={len(self.instructions)!r}, recent_blockhash={self.recent_blockhash!r})"


class TransactionType(TypedDict):
    '''
    JSON Response type of Transaction Information received by RPC
    '''
    message: MessageType
    signatures: List[str]


class Transaction:
    '''
    Convert Transaction JSON to Class
    '''

    def __init__(self, response: TransactionType) -> None:
        message = Message(response['message'])
        self.message = CoreMessage(
            header=message.header,
            account_keys=message.account_keys,
            instructions=message.instructions,
            recent_blockhash=message.recent_blockhash
        )
        self.signatures = response['signatures']

    def __repr__(self) -> str:
        return f"Transaction(message={self.message!r}, signatures={self.signatures!r})"


class MetaType(TypedDict):
    '''
    JSON Response type of Meta Information received by RPC
    '''
    err: Union[Any, None]
    fee: int
    innerInstructions: List[Any]
    logMessages: List[Any]
    postBalances: List[int]
    postTokenBalances: List[Any]
    preBalances: List[int]
    preTokenBalances: List[Any]
    rewards: Union[Any, None]


class Meta:
    '''
    Convert Meta JSON to Class
    '''

    def __init__(self, response: MetaType) -> None:
        self.err = response['err']
        self.fee = response['fee']
        self.inner_instructions = response['innerInstructions']
        self.log_messages = response['logMessages']
        self.post_balances = response['postBalances']
        self.post_token_balances = response['postTokenBalances']
        self.pre_balances = response['preBalances']
        self.pre_token_balances = response['preTokenBalances']
        self.rewards = response['rewards']

    def __repr__(self) -> str:
        return f"Meta(err={self.err!r}, fee={self.fee!r}, num_inner_instructions={len(self.inner_instructions)!r})"


class TransactionElementType(TypedDict):
    '''
    JSON Response type of Transaction Information received by RPC
    '''
    meta: MetaType
    transaction: TransactionType


class TransactionElement:
    '''
    Convert Transaction JSON to Class
    '''

    def __init__(self, response: TransactionElementType) -> None:
        self.meta = Meta(response['meta'])
        self.transaction = Transaction(response['transaction'])

    def __repr__(self) -> str:
        return f"TransactionElement(signatures={self.transaction.signatures!r})"


class BlockType(TypedDict):
    '''
    JSON Response type of Block Information received by RPC
    '''
    blockHeight: int
    blockTime: None
    blockhash: str
    parentSlot: int
    previousBlockhash: str
    transactions: List[TransactionElementType]


class Block:
    '''
    Convert Block JSON to Class
    '''

    def __init__(self, response: BlockType) -> None:
        self.block_height = response['blockHeight']
        self.block_time = response['blockTime']
        self.blockhash = response['blockhash']
        self.parent_slot = response['parentSlot']
        self.previous_blockhash = response['previousBlockhash']
        self.transactions = [TransactionElement(
            transaction) for transaction in response.get('transactions', [])]

    def __repr__(self) -> str:
        return f"Block(block_height={self.block_height!r}, block_time={self.block_time!r}, blockhash={self.blockhash!r},num_transactions={len(self.transactions)!r})"


class RangeType(TypedDict):
    '''
    JSON Response type of Range Information received by RPC
    '''
    firstSlot: int
    lastSlot: int


class Range:
    '''
    Convert Range JSON to Class
    '''

    def __init__(self, response: RangeType) -> None:
        self.first_slot = response['firstSlot']
        self.last_slot = response['lastSlot']

    def __repr__(self) -> str:
        return f"Range(first_slot={self.first_slot!r}, last_slot={self.last_slot!r})"


class BlockProductionType(TypedDict):
    '''
    JSON Response type of Block Production Information received by RPC
    '''
    byIdentity: Dict[str, Any]
    range: RangeType


class BlockProduction:
    '''
    Convert Block Production JSON to Class
    '''

    def __init__(self, response: BlockProductionType) -> None:
        self.by_identity = response['byIdentity']
        self.range = Range(response['range'])

    def __repr__(self) -> str:
        return f"BlockProduction(by_identity={self.by_identity!r}, range={self.range!r})"


class BlockCommitmentType(TypedDict):
    '''
    JSON Response type of Block Commitment Information received by RPC
    '''
    commitment: List[int]
    totalStake: int


class BlockCommitment:
    '''
    Convert Block Commitment JSON to Class
    '''

    def __init__(self, response: BlockCommitmentType) -> None:
        self.commitment = response['commitment']
        self.total_stake = response['totalStake']

    def __repr__(self) -> str:
        return f"BlockCommitment(commitment={self.commitment!r}, total_stake={self.total_stake!r})"


class FeeCalculatorType(TypedDict):
    '''
    JSON Response type of Fee Calculator Information received by RPC
    '''
    lamportsPerSignature: int


class FeeCalculator:
    '''
    Convert Fee Calculator JSON to Class
    '''

    def __init__(self, response: FeeCalculatorType) -> None:
        self.lamports_per_signature = response['lamportsPerSignature']

    def __repr__(self) -> str:
        return f"FeeCalculator(lamports_per_signature={self.lamports_per_signature!r})"


class BlockHashType(TypedDict):
    '''
    JSON Response type of Block Hash Information received by RPC
    '''
    blockhash: str
    feeCalculator: FeeCalculatorType


class BlockHash:
    '''
    Convert Block Hash JSON to Class
    '''

    def __init__(self, response: BlockHashType) -> None:
        self.blockhash = response['blockhash']
        if "feeCalculator" in response:
            self.fee_calculator = FeeCalculator(response['feeCalculator'])
        else:
            self.fee_calculator = None

    def __repr__(self) -> str:
        return f"BlockHash(blockhash={self.blockhash!r}, fee_calculator={self.fee_calculator!r})"
