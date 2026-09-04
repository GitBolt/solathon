from typing import Any, NotRequired, TypedDict

from solathon.core.message import MessageHeader
from solathon.publickey import PublicKey


class HeaderType(TypedDict):
    """
    JSON Response type of Header Information received by RPC
    """

    numReadonlySignedAccounts: int
    numReadonlyUnsignedAccounts: int
    numRequiredSignatures: int


class Header:
    def __init__(self, response: HeaderType) -> None:
        self.raw = response
        self.num_readonly_signed_accounts = response["numReadonlySignedAccounts"]
        self.num_readonly_unsigned_accounts = response["numReadonlyUnsignedAccounts"]
        self.num_required_signatures = response["numRequiredSignatures"]

    def __repr__(self) -> str:
        return f"Header(num_required_signatures={self.num_required_signatures!r}, num_readonly_signed_accounts={self.num_readonly_signed_accounts!r}, num_readonly_unsigned_accounts={self.num_readonly_unsigned_accounts!r})"


class InstructionType(TypedDict, total=False):
    """
    JSON Response type of Instruction Information received by RPC
    """

    accounts: list[int | str]
    data: str
    programIdIndex: int
    stackHeight: int | None


class Instruction:
    """
    Convert Instruction JSON to Class
    """

    def __init__(self, response: InstructionType) -> None:
        self.raw = response
        self.accounts = response.get("accounts", [])
        self.data = response.get("data")
        self.program_id_index = response.get("programIdIndex")
        self.program = response.get("program")
        self.program_id = response.get("programId")
        self.parsed = response.get("parsed")
        self.stack_height = response.get("stackHeight")

    def __repr__(self) -> str:
        return f"Instruction(num_accounts={len(self.accounts)!r}, program_id_index={self.program_id_index!r})"


class MessageType(TypedDict, total=False):
    """
    JSON Response type of Message Information received by RPC
    """

    accountKeys: list[str | dict[str, Any]]
    header: HeaderType
    instructions: list[InstructionType]
    recentBlockhash: str
    addressTableLookups: list[dict[str, Any]] | None
    transactionConfig: dict[str, Any]


class Message:
    """
    Convert Message JSON to Class
    """

    def __init__(self, response: MessageType) -> None:
        self.raw = response
        self.account_key_details = response["accountKeys"]
        self.account_keys = [
            PublicKey(entry["pubkey"] if isinstance(entry, dict) else entry)
            for entry in self.account_key_details
        ]
        header = Header(response["header"])
        self.header = MessageHeader(
            num_required_signatures=header.num_required_signatures,
            num_readonly_signed_accounts=header.num_readonly_signed_accounts,
            num_readonly_unsigned_accounts=header.num_readonly_unsigned_accounts,
        )
        self.instructions = [
            Instruction(instruction) for instruction in response["instructions"]
        ]
        self.recent_blockhash = response["recentBlockhash"]
        self.address_table_lookups = response.get("addressTableLookups") or []
        self.transaction_config = response.get("transactionConfig")

    def is_account_signer(self, index: int) -> bool:
        if not 0 <= index < len(self.account_keys):
            raise IndexError("Account index is outside the message")
        detail = self.account_key_details[index]
        if isinstance(detail, dict) and "signer" in detail:
            return bool(detail["signer"])
        return index < self.header.num_required_signatures

    def is_account_writable(self, index: int) -> bool:
        if not 0 <= index < len(self.account_keys):
            raise IndexError("Account index is outside the message")
        detail = self.account_key_details[index]
        if isinstance(detail, dict) and "writable" in detail:
            return bool(detail["writable"])
        writable_signers = (
            self.header.num_required_signatures
            - self.header.num_readonly_signed_accounts
        )
        writable_unsigned_limit = (
            len(self.account_keys) - self.header.num_readonly_unsigned_accounts
        )
        return index < writable_signers or (
            self.header.num_required_signatures <= index < writable_unsigned_limit
        )

    def __repr__(self) -> str:
        return f"Message(header={self.header!r}, num_instructions={len(self.instructions)!r}, recent_blockhash={self.recent_blockhash!r})"


class TransactionType(TypedDict):
    """
    JSON Response type of Transaction Information received by RPC
    """

    message: MessageType
    signatures: list[str]


class Transaction:
    """
    Convert Transaction JSON to Class
    """

    def __init__(self, response: TransactionType) -> None:
        self.raw = response
        self.message = Message(response["message"])
        self.signatures = response["signatures"]

    def __repr__(self) -> str:
        return f"Transaction(message={self.message!r}, signatures={self.signatures!r})"


class MetaType(TypedDict, total=False):
    """
    JSON Response type of Meta Information received by RPC
    """

    err: Any | None
    fee: int
    innerInstructions: list[Any] | None
    logMessages: list[Any] | None
    postBalances: list[int]
    postTokenBalances: list[Any]
    preBalances: list[int]
    preTokenBalances: list[Any]
    rewards: Any | None
    loadedAddresses: dict[str, list[str]]
    returnData: dict[str, Any] | None
    computeUnitsConsumed: int
    costUnits: int
    loadedAccountsDataSize: int
    status: dict[str, Any]


class Meta:
    """
    Convert Meta JSON to Class
    """

    def __init__(self, response: MetaType) -> None:
        self.raw = response
        self.err = response.get("err")
        self.fee = response.get("fee")
        self.inner_instructions = response.get("innerInstructions")
        self.log_messages = response.get("logMessages")
        self.post_balances = response.get("postBalances", [])
        self.post_token_balances = response.get("postTokenBalances")
        self.pre_balances = response.get("preBalances", [])
        self.pre_token_balances = response.get("preTokenBalances")
        self.rewards = response.get("rewards")
        loaded_addresses = response.get("loadedAddresses") or {}
        self.loaded_addresses = loaded_addresses
        self.loaded_writable_addresses = loaded_addresses.get("writable", [])
        self.loaded_readonly_addresses = loaded_addresses.get("readonly", [])
        self.return_data = response.get("returnData")
        self.compute_units_consumed = response.get("computeUnitsConsumed")
        self.cost_units = response.get("costUnits")
        self.loaded_accounts_data_size = response.get("loadedAccountsDataSize")
        self.status = response.get("status")

    def __repr__(self) -> str:
        inner_count = len(self.inner_instructions or [])
        return (
            f"Meta(err={self.err!r}, fee={self.fee!r}, "
            f"num_inner_instructions={inner_count!r})"
        )


class TransactionElementType(TypedDict, total=False):
    """
    JSON Response type of Transaction Information received by RPC
    """

    meta: MetaType | None
    transaction: TransactionType
    blockTime: int | None
    slot: int
    version: str | int


class TransactionElement:
    """
    Convert Transaction JSON to Class
    """

    def __init__(self, response: TransactionElementType) -> None:
        self.raw = response
        meta = response.get("meta")
        self.meta = Meta(meta) if meta is not None else None
        self.transaction = Transaction(response["transaction"])
        self.block_time = response.get("blockTime")
        self.slot = response.get("slot")
        self.version = response.get("version")

    def __repr__(self) -> str:
        return f"TransactionElement(signatures={self.transaction.signatures!r})"


class BlockType(TypedDict, total=False):
    """
    JSON Response type of Block Information received by RPC
    """

    blockHeight: int | None
    blockTime: int | None
    blockhash: str
    parentSlot: int
    previousBlockhash: str
    transactions: list[TransactionElementType]
    signatures: list[str]
    rewards: list[dict[str, Any]] | None
    numRewardPartitions: int | None


class Block:
    """
    Convert Block JSON to Class
    """

    def __init__(self, response: BlockType) -> None:
        self.raw = response
        self.block_height = response.get("blockHeight")
        self.block_time = response.get("blockTime")
        self.blockhash = response["blockhash"]
        self.parent_slot = response["parentSlot"]
        self.previous_blockhash = response["previousBlockhash"]
        self.transactions = [
            TransactionElement(transaction)
            for transaction in response.get("transactions", [])
        ]
        self.signatures = response.get("signatures", [])
        self.rewards = response.get("rewards")
        self.num_reward_partitions = response.get("numRewardPartitions")

    def __repr__(self) -> str:
        return f"Block(block_height={self.block_height!r}, block_time={self.block_time!r}, blockhash={self.blockhash!r},num_transactions={len(self.transactions)!r})"


class RangeType(TypedDict):
    """
    JSON Response type of Range Information received by RPC
    """

    firstSlot: int
    lastSlot: int


class Range:
    """
    Convert Range JSON to Class
    """

    def __init__(self, response: RangeType) -> None:
        self.raw = response
        self.first_slot = response["firstSlot"]
        self.last_slot = response["lastSlot"]

    def __repr__(self) -> str:
        return f"Range(first_slot={self.first_slot!r}, last_slot={self.last_slot!r})"


class BlockProductionType(TypedDict):
    """
    JSON Response type of Block Production Information received by RPC
    """

    byIdentity: dict[str, Any]
    range: RangeType


class BlockProduction:
    """
    Convert Block Production JSON to Class
    """

    def __init__(self, response: BlockProductionType) -> None:
        self.raw = response
        self.context: dict[str, Any] | None = None
        self.by_identity = response["byIdentity"]
        self.range = Range(response["range"])

    def __repr__(self) -> str:
        return (
            f"BlockProduction(by_identity={self.by_identity!r}, range={self.range!r})"
        )


class BlockCommitmentType(TypedDict):
    """
    JSON Response type of Block Commitment Information received by RPC
    """

    commitment: list[int]
    totalStake: int


class BlockCommitment:
    """
    Convert Block Commitment JSON to Class
    """

    def __init__(self, response: BlockCommitmentType) -> None:
        self.raw = response
        self.commitment = response["commitment"]
        self.total_stake = response["totalStake"]

    def __repr__(self) -> str:
        return f"BlockCommitment(commitment={self.commitment!r}, total_stake={self.total_stake!r})"


class FeeCalculatorType(TypedDict):
    """
    JSON Response type of Fee Calculator Information received by RPC
    """

    lamportsPerSignature: int


class FeeCalculator:
    """
    Convert Fee Calculator JSON to Class
    """

    def __init__(self, response: FeeCalculatorType) -> None:
        self.raw = response
        self.lamports_per_signature = response["lamportsPerSignature"]

    def __repr__(self) -> str:
        return f"FeeCalculator(lamports_per_signature={self.lamports_per_signature!r})"


class BlockHashType(TypedDict):
    """
    JSON Response type of Block Hash Information received by RPC
    """

    blockhash: str
    lastValidBlockHeight: int
    feeCalculator: NotRequired[FeeCalculatorType]


class BlockHash:
    """
    Convert Block Hash JSON to Class
    """

    def __init__(self, response: BlockHashType) -> None:
        self.raw = response
        self.blockhash = response["blockhash"]
        self.last_valid_block_height = response.get("lastValidBlockHeight")
        self.context: dict[str, Any] | None = None
        self.fee_calculator: FeeCalculator | None
        if "feeCalculator" in response:
            self.fee_calculator = FeeCalculator(response["feeCalculator"])
        else:
            self.fee_calculator = None

    def __repr__(self) -> str:
        return f"BlockHash(blockhash={self.blockhash!r}, fee_calculator={self.fee_calculator!r})"
