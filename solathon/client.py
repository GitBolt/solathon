from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Text, Union

from .utils import RPCRequestError, validate_commitment
from .publickey import PublicKey
from .core.http import HTTPClient
from .transaction import Transaction
from .core.types import (
    BlockHash,
    BlockHashType,
    Commitment,
    LargestAccounts,
    LargestAccountsType,
    PubKeyIdentity,
    PubKeyIdentityType,
    RPCResponse,
    AccountInfo,
    AccountInfoType,
    Block,
    BlockType,
    BlockProductionType,
    BlockProduction,
    BlockCommitmentType,
    BlockCommitment,
    ClusterNode,
    ClusterNodeType,
    Epoch,
    EpochType,
    EpochSchedule,
    EpochScheduleType,
    InflationGovernor,
    InflationGovernorType,
    InflationRate,
    InflationRateType,
    InflationReward,
    InflationRewardType,
    ProgramAccount,
    ProgramAccountType,
    RecentPerformanceSamples,
    RecentPerformanceSamplesType,
    SignatureStatus,
    SignatureStatusType,
    Supply,
    SupplyType,
    TransactionSignature,
    TransactionSignatureType,
    TransactionElement,
    TransactionElementType,
)


class Client:
    def __init__(
        self, endpoint: Text, local: bool = False, clean_response: bool = True
    ):
        """
        Initializes the Solana RPC client.

        Args:
            endpoint (str): The RPC endpoint URL (any valid HTTP/HTTPS URL).
            local (bool, optional): Whether to skip endpoint validation. Defaults to False.
            clean_response (bool, optional): Whether to unwrap RPC responses. Defaults to True.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError(
                "Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL."
            )
        self.http = HTTPClient(endpoint)
        self.endpoint = endpoint
        self.clean_response = clean_response

    def refresh_http(self) -> None:
        self.http.refresh()

    # ========================================================================
    # Account Methods
    # ========================================================================

    def get_account_info(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[AccountInfoType] | AccountInfo:
        """Returns all account info for the specified public key."""
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getAccountInfo", [str(public_key), config])
        if self.clean_response:
            if response["value"] is None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            return AccountInfo(response["value"])
        return response

    def get_balance(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns the lamport balance of the account."""
        params: list = [str(public_key)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_multiple_accounts(
        self, pubkeys: List[str], commitment: Optional[Commitment] = None
    ) -> RPCResponse[List[AccountInfoType]] | List[AccountInfo]:
        """Returns account info for a list of public keys."""
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getMultipleAccounts", [pubkeys, config])
        if self.clean_response:
            return [AccountInfo(account) for account in response["value"] if account]
        return response

    def get_program_accounts(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None,
        filters: Optional[List[Dict]] = None
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """Returns all accounts owned by the specified program."""
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        if filters:
            config["filters"] = filters
        response = self.build_and_send_request("getProgramAccounts", [str(public_key), config])
        if self.clean_response:
            return [ProgramAccount(account) for account in response]
        return response

    def get_largest_accounts(
        self, commitment: Optional[Commitment] = None, filter: Optional[Literal["circulating", "nonCirculating"]] = None
    ) -> RPCResponse[List[LargestAccountsType]] | List[LargestAccounts]:
        """Returns the 20 largest accounts by lamport balance."""
        config: Dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if filter:
            config["filter"] = filter
        response = self.build_and_send_request("getLargestAccounts", [config] if config else [None])
        if self.clean_response:
            return [LargestAccounts(account) for account in response["value"]]
        return response

    def get_minimum_balance_for_rent_exemption(
        self, data_length: int, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns minimum balance required to make account rent-exempt."""
        params: list = [data_length]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getMinimumBalanceForRentExemption", params)

    # ========================================================================
    # Block Methods
    # ========================================================================

    def get_block(
        self, slot: int, commitment: Optional[Commitment] = None,
        max_supported_transaction_version: Optional[int] = 0
    ) -> RPCResponse[BlockType] | Block:
        """Returns identity and transaction info about a confirmed block."""
        config: Dict[str, Any] = {"maxSupportedTransactionVersion": max_supported_transaction_version}
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getBlock", [slot, config])
        if self.clean_response:
            return Block(response)
        return response

    def get_block_height(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns the current block height."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getBlockHeight", params if params else [None])

    def get_block_production(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[BlockProductionType] | BlockProduction:
        """Returns recent block production information."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getBlockProduction", params if params else [None])
        if self.clean_response:
            return BlockProduction(response["value"])
        return response

    def get_block_commitment(
        self, block: int
    ) -> RPCResponse[BlockCommitmentType] | BlockCommitment:
        """Returns commitment for a particular block."""
        response = self.build_and_send_request("getBlockCommitment", [block])
        if self.clean_response:
            return BlockCommitment(response)
        return response

    def get_blocks(
        self, start_slot: int, end_slot: int | None = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[List[int]] | List[int]:
        """Returns a list of confirmed blocks between two slots."""
        params: list = [start_slot]
        if end_slot:
            params.append(end_slot)
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getBlocks", params)

    def get_blocks_with_limit(
        self, start_slot: int, limit: int
    ) -> RPCResponse[List[int]] | List[int]:
        """Returns a list of confirmed blocks starting at the given slot."""
        return self.build_and_send_request("getBlocksWithLimit", [start_slot, limit])

    def get_block_time(self, block: int) -> RPCResponse[int] | int:
        """Returns the estimated production time of a block."""
        return self.build_and_send_request("getBlockTime", [block])

    def get_latest_blockhash(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[BlockHashType] | BlockHash:
        """Returns the latest blockhash."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getLatestBlockhash", params if params else [None])
        if self.clean_response:
            return BlockHash(response["value"])
        return response

    def is_blockhash_valid(
        self, blockhash: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[bool] | bool:
        """Returns whether a blockhash is still valid."""
        params: list = [blockhash]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("isBlockhashValid", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Cluster Methods
    # ========================================================================

    def get_cluster_nodes(self) -> RPCResponse[List[ClusterNodeType]] | List[ClusterNode]:
        """Returns information about all nodes participating in the cluster."""
        response = self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(node) for node in response]
        return response

    def get_epoch_info(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[EpochType] | Epoch:
        """Returns information about the current epoch."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getEpochInfo", params if params else [None])
        if self.clean_response:
            return Epoch(response)
        return response

    def get_epoch_schedule(self) -> RPCResponse[EpochScheduleType] | EpochSchedule:
        """Returns the epoch schedule."""
        response = self.build_and_send_request("getEpochSchedule", [None])
        if self.clean_response:
            return EpochSchedule(response)
        return response

    def get_first_available_block(self) -> RPCResponse[int] | int:
        """Returns the slot of the lowest confirmed block."""
        return self.build_and_send_request("getFirstAvailableBlock", [None])

    def get_genesis_hash(self) -> RPCResponse[str] | str:
        """Returns the genesis hash."""
        return self.build_and_send_request("getGenesisHash", [None])

    def get_health(self) -> RPCResponse[Literal["ok"]] | Literal["ok"]:
        """Returns the current health of the node."""
        return self.build_and_send_request("getHealth", [None])

    def get_identity(self) -> RPCResponse[PubKeyIdentityType] | PubKeyIdentity:
        """Returns the identity pubkey of the current node."""
        response = self.build_and_send_request("getIdentity", [None])
        if self.clean_response:
            return PubKeyIdentity(response)
        return response

    def get_version(self) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """Returns the current Solana version running on the node."""
        return self.build_and_send_request("getVersion", [None])

    def get_highest_snapshot_slot(self) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """Returns the highest slot info that the node has snapshots for."""
        return self.build_and_send_request("getHighestSnapshotSlot", [None])

    def get_leader_schedule(
        self, slot: Optional[int] = None, commitment: Optional[Commitment] = None
    ) -> RPCResponse[Dict[str, List[int]]] | Dict[str, List[int]]:
        """Returns the leader schedule for an epoch."""
        params: list = [slot]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getLeaderSchedule", params)

    def get_max_retransmit_slot(self) -> RPCResponse[int] | int:
        """Returns the max slot seen from retransmit stage."""
        return self.build_and_send_request("getMaxRetransmitSlot", [None])

    def get_max_shred_insert_slot(self) -> RPCResponse[int] | int:
        """Returns the max slot seen from after shred insert."""
        return self.build_and_send_request("getMaxShredInsertSlot", [None])

    def get_slot(self, commitment: Optional[Commitment] = None) -> RPCResponse[int] | int:
        """Returns the current slot."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getSlot", params if params else [None])

    def get_slot_leader(self, commitment: Optional[Commitment] = None) -> RPCResponse[str] | str:
        """Returns the current slot leader."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getSlotLeader", params if params else [None])

    def get_slot_leaders(
        self, start_slot: int, limit: int
    ) -> RPCResponse[List[str]] | List[str]:
        """Returns the slot leaders for a given slot range."""
        return self.build_and_send_request("getSlotLeaders", [start_slot, limit])

    def minimum_ledger_slot(self) -> RPCResponse[int] | int:
        """Returns the lowest slot that the node has info about in its ledger."""
        return self.build_and_send_request("minimumLedgerSlot", [None])

    def get_vote_accounts(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """Returns the account info and associated stake for all voting accounts."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getVoteAccounts", params if params else [None])

    # ========================================================================
    # Fee Methods
    # ========================================================================

    def get_fee_for_message(
        self, message: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns the fee for a given message (base64-encoded)."""
        params: list = [message]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getFeeForMessage", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_recent_prioritization_fees(
        self, addresses: Optional[List[Text]] = None
    ) -> RPCResponse[List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """Returns recent prioritization fees from recent blocks."""
        params: list = []
        if addresses:
            params.append(addresses)
        return self.build_and_send_request("getRecentPrioritizationFees", params if params else [None])

    # ========================================================================
    # Inflation Methods
    # ========================================================================

    def get_inflation_governor(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[InflationGovernorType] | InflationGovernor:
        """Returns the current inflation governor."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getInflationGovernor", params if params else [None])
        if self.clean_response:
            return InflationGovernor(response)
        return response

    def get_inflation_rate(self) -> RPCResponse[InflationRateType] | InflationRate:
        """Returns the specific inflation values for the current epoch."""
        response = self.build_and_send_request("getInflationRate", [None])
        if self.clean_response:
            return InflationRate(response)
        return response

    def get_inflation_reward(
        self, addresses: List[Text], commitment: Optional[Commitment] = None,
        epoch: Optional[int] = None
    ) -> RPCResponse[List[InflationRewardType]] | List[InflationReward]:
        """Returns the inflation / staking reward for a list of addresses."""
        params: list = [addresses]
        config: Dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if epoch is not None:
            config["epoch"] = epoch
        if config:
            params.append(config)
        response = self.build_and_send_request("getInflationReward", params)
        if self.clean_response:
            return [InflationReward(reward) for reward in response if reward]
        return response

    # ========================================================================
    # Supply Methods
    # ========================================================================

    def get_supply(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[SupplyType] | Supply:
        """Returns information about the current supply."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getSupply", params if params else [None])
        if self.clean_response:
            return Supply(response["value"])
        return response

    # ========================================================================
    # Stake Methods
    # ========================================================================

    def get_stake_minimum_delegation(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns the stake minimum delegation in lamports."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getStakeMinimumDelegation", params if params else [None])
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Token Methods
    # ========================================================================

    def get_token_accounts_by_owner(
        self, public_key: Text | PublicKey, commitment: Optional[Commitment] = None,
        **kwargs,
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """Returns all SPL Token accounts by owner."""
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError("You must pass either mint_id or program_id keyword argument")
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        encoding = kwargs.get("encoding", "jsonParsed")

        config: Dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))

        response = self.build_and_send_request(
            "getTokenAccountsByOwner",
            [str(public_key), {"mint": mint_id} if mint_id else {"programId": program_id}, config],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_token_accounts_by_delegate(
        self, delegate: Text | PublicKey, commitment: Optional[Commitment] = None,
        **kwargs,
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """Returns all SPL Token accounts approved by a delegate."""
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError("You must pass either mint_id or program_id keyword argument")
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        encoding = kwargs.get("encoding", "jsonParsed")

        config: Dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))

        response = self.build_and_send_request(
            "getTokenAccountsByDelegate",
            [str(delegate), {"mint": mint_id} if mint_id else {"programId": program_id}, config],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_token_account_balance(
        self, token_account: Text | PublicKey, commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """Returns the token balance of an SPL Token account."""
        params: list = [str(token_account)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getTokenAccountBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_token_supply(
        self, mint: Text | PublicKey, commitment: Optional[Commitment] = None
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """Returns the total supply of an SPL Token."""
        params: list = [str(mint)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getTokenSupply", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_token_largest_accounts(
        self, mint: Text | PublicKey, commitment: Optional[Commitment] = None
    ) -> RPCResponse[List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """Returns the 20 largest accounts for an SPL Token."""
        params: list = [str(mint)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getTokenLargestAccounts", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Transaction Methods
    # ========================================================================

    def get_transaction(
        self, signature: Text,
        max_supported_transaction_version: Optional[int] = 0,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[TransactionElementType] | TransactionElement:
        """Returns transaction details for a confirmed transaction."""
        config: Dict[str, Any] = {
            "maxSupportedTransactionVersion": max_supported_transaction_version,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getTransaction", [signature, config])
        if self.clean_response:
            if response is None:
                raise ValueError("Transaction not found")
            return TransactionElement(response)
        return response

    def get_transaction_count(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """Returns the current transaction count from the ledger."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getTransactionCount", params if params else [None])

    def get_signatures_for_address(
        self, acct_address: Text,
        limit: Optional[int] = None,
        before: Optional[Text] = None,
        until: Optional[Text] = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[List[TransactionSignatureType]] | List[TransactionSignature]:
        """Returns signatures for confirmed transactions involving an address."""
        params: list = [acct_address]
        options: Dict[str, Any] = {}
        if limit is not None:
            options["limit"] = limit
        if before is not None:
            options["before"] = before
        if until is not None:
            options["until"] = until
        if commitment:
            options.update(validate_commitment(commitment))
        if options:
            params.append(options)
        response = self.build_and_send_request("getSignaturesForAddress", params)
        if self.clean_response:
            return [TransactionSignature(sig) for sig in response]
        return response

    def get_signature_statuses(
        self, transaction_sigs: List[Text], search_transaction_history: bool = False
    ) -> RPCResponse[List[SignatureStatusType]] | List[SignatureStatus]:
        """Returns the statuses of a list of signatures."""
        params: list = [transaction_sigs]
        if search_transaction_history:
            params.append({"searchTransactionHistory": True})
        response = self.build_and_send_request("getSignatureStatuses", params)
        if self.clean_response:
            return [SignatureStatus(status) for status in response["value"] if status]
        return response

    def get_recent_performance_samples(
        self, limit: Optional[int] = None
    ) -> RPCResponse[List[RecentPerformanceSamplesType]] | List[RecentPerformanceSamples]:
        """Returns a list of recent performance samples."""
        params: list = [limit] if limit else [None]
        response = self.build_and_send_request("getRecentPerformanceSamples", params)
        if self.clean_response:
            return [RecentPerformanceSamples(sample) for sample in response]
        return response

    def simulate_transaction(
        self, transaction: Text,
        sig_verify: bool = False,
        commitment: Optional[Commitment] = None,
        replace_recent_blockhash: bool = False,
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """Simulates sending a transaction (base64-encoded)."""
        config: Dict[str, Any] = {
            "encoding": "base64",
            "sigVerify": sig_verify,
            "replaceRecentBlockhash": replace_recent_blockhash,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("simulateTransaction", [transaction, config])
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Action Methods (non-get)
    # ========================================================================

    def request_airdrop(
        self, public_key: PublicKey | Text, lamports: int,
        commitment: Optional[Commitment] = None
    ) -> RPCResponse[str] | str:
        """Requests an airdrop of lamports to the specified public key."""
        params: list = [str(public_key), lamports]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("requestAirdrop", params)

    def send_transaction(
        self, transaction: Transaction, options: Optional[Dict] = None
    ) -> RPCResponse[str] | str:
        """Signs and sends a transaction to the network."""
        recent_blockhash = transaction.recent_blockhash
        if recent_blockhash is None:
            blockhash_resp = self.get_latest_blockhash()
            recent_blockhash = blockhash_resp.blockhash

        if options is None:
            options = {"encoding": "base64"}

        transaction.recent_blockhash = recent_blockhash
        transaction.sign()

        return self.build_and_send_request(
            "sendTransaction", [transaction.serialize(), options]
        )

    # ========================================================================
    # Internal
    # ========================================================================

    def build_and_send_request(
        self, method: str, params: List[Any]
    ) -> RPCResponse | Dict[str, Any] | List[Dict[str, Any]]:
        """Builds and sends an RPC request."""
        data: Dict[str, Any] = self.http.build_data(method=method, params=params)
        res: RPCResponse = self.http.send(data)
        if self.clean_response:
            if "error" in res:
                raise RPCRequestError(
                    f"RPC Error {res['error']['code']}: {res['error']['message']}"
                )
            result = res.get("result")
            if result is None or isinstance(result, (dict, list, str, int, float, bool)):
                return result
            else:
                raise RPCRequestError(
                    f"Unexpected response type: {type(result).__name__}"
                )
        return res
