from __future__ import annotations

import time
from typing import Any, Literal

import httpx

from .core.http import HTTPClient
from .core.rpc import (
    DEFAULT_BLOCKHASH,
    block_height_value,
    commitment_reached,
    latest_blockhash_value,
    response_context_slot,
    signature_status_payload,
    token_program_ids,
    transaction_signature_value,
    unwrap_rpc_envelope,
    validate_confirmation_polling,
)
from .core.types import (
    AccountInfo,
    AccountInfoType,
    Block,
    BlockCommitment,
    BlockCommitmentType,
    BlockHash,
    BlockHashType,
    BlockProduction,
    BlockProductionType,
    BlockType,
    ClusterNode,
    ClusterNodeType,
    Commitment,
    Epoch,
    EpochSchedule,
    EpochScheduleType,
    EpochType,
    InflationGovernor,
    InflationGovernorType,
    InflationRate,
    InflationRateType,
    InflationReward,
    InflationRewardType,
    LargestAccounts,
    LargestAccountsType,
    ProgramAccount,
    ProgramAccountType,
    PubKeyIdentity,
    PubKeyIdentityType,
    RecentPerformanceSamples,
    RecentPerformanceSamplesType,
    RPCResponse,
    SignatureStatus,
    SignatureStatusType,
    Supply,
    SupplyType,
    TransactionElement,
    TransactionElementType,
    TransactionSignature,
    TransactionSignatureType,
)
from .publickey import PublicKey
from .transaction import Transaction
from .utils import RPCRequestError, validate_commitment
from .versioned import VersionedTransaction


class Client:
    def __init__(
        self,
        endpoint: str,
        local: bool = False,
        clean_response: bool = True,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ):
        """
        Initializes the Solana RPC client.

        Args:
            endpoint (str): The RPC endpoint URL (any valid HTTP/HTTPS URL).
            local (bool, optional): Whether to skip endpoint validation. Defaults to False.
            clean_response (bool, optional): Whether to unwrap RPC responses. Defaults to True.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL.")
        self.http = HTTPClient(endpoint, timeout=timeout, client=http_client)
        self.endpoint = endpoint
        self.clean_response = clean_response

    def refresh_http(self) -> None:
        self.http.refresh()

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ========================================================================
    # Account Methods
    # ========================================================================

    def get_account_info(
        self,
        public_key: PublicKey | str,
        commitment: Commitment | None = None,
        encoding: str = "base64",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[AccountInfoType] | AccountInfo:
        """Returns all account info for the specified public key."""
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = self.build_and_send_request(
            "getAccountInfo", [str(public_key), config]
        )
        if self.clean_response:
            if response["value"] is None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            account = AccountInfo(response["value"])
            account.context = response.get("context")
            return account
        return response

    def get_balance(
        self,
        public_key: PublicKey | str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        """Returns the lamport balance of the account."""
        params: list = [str(public_key)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_multiple_accounts(
        self,
        pubkeys: list[PublicKey | str],
        commitment: Commitment | None = None,
        encoding: str = "base64",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[AccountInfoType | None]] | list[AccountInfo | None]:
        """Returns account info for a list of public keys."""
        if not 1 <= len(pubkeys) <= 100:
            raise ValueError("pubkeys must contain between 1 and 100 addresses")
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = self.build_and_send_request(
            "getMultipleAccounts", [[str(pubkey) for pubkey in pubkeys], config]
        )
        if self.clean_response:
            return [
                AccountInfo(account) if account is not None else None
                for account in response["value"]
            ]
        return response

    def get_program_accounts(
        self,
        public_key: PublicKey | str,
        commitment: Commitment | None = None,
        filters: list[dict] | None = None,
        encoding: str = "base64",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
        with_context: bool | None = None,
        sort_results: bool | None = None,
    ) -> RPCResponse[list[ProgramAccountType]] | list[ProgramAccount] | dict[str, Any]:
        """Returns all accounts owned by the specified program."""
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if filters is not None:
            config["filters"] = filters
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if with_context is not None:
            config["withContext"] = with_context
        if sort_results is not None:
            config["sortResults"] = sort_results
        response = self.build_and_send_request(
            "getProgramAccounts", [str(public_key), config]
        )
        if self.clean_response:
            if with_context:
                return response
            return [ProgramAccount(account) for account in response]
        return response

    def get_largest_accounts(
        self,
        commitment: Commitment | None = None,
        filter: Literal["circulating", "nonCirculating"] | None = None,
        sort_results: bool | None = None,
    ) -> RPCResponse[list[LargestAccountsType]] | list[LargestAccounts]:
        """Returns the 20 largest accounts by lamport balance."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if filter:
            config["filter"] = filter
        if sort_results is not None:
            config["sortResults"] = sort_results
        response = self.build_and_send_request(
            "getLargestAccounts", [config] if config else [None]
        )
        if self.clean_response:
            return [LargestAccounts(account) for account in response["value"]]
        return response

    def get_minimum_balance_for_rent_exemption(
        self,
        acct_length: int | None = None,
        commitment: Commitment | None = None,
        *,
        data_length: int | None = None,
    ) -> RPCResponse[int] | int:
        """Returns minimum balance required to make account rent-exempt."""
        if acct_length is None:
            acct_length = data_length
        elif data_length is not None:
            raise TypeError("Pass acct_length or data_length, not both")
        if acct_length is None:
            raise TypeError("acct_length is required")
        params: list = [acct_length]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getMinimumBalanceForRentExemption", params)

    # ========================================================================
    # Block Methods
    # ========================================================================

    def get_block(
        self,
        slot: int,
        commitment: Commitment | None = None,
        max_supported_transaction_version: int | None = 0,
        encoding: str | None = None,
        transaction_details: Literal["full", "accounts", "signatures", "none"]
        | None = None,
        rewards: bool | None = None,
    ) -> RPCResponse[BlockType] | Block | dict[str, Any] | None:
        """Returns identity and transaction info about a confirmed block."""
        config: dict[str, Any] = {}
        if max_supported_transaction_version is not None:
            config["maxSupportedTransactionVersion"] = max_supported_transaction_version
        if commitment:
            config.update(validate_commitment(commitment))
        if encoding is not None:
            config["encoding"] = encoding
        if transaction_details is not None:
            config["transactionDetails"] = transaction_details
        if rewards is not None:
            config["rewards"] = rewards
        response = self.build_and_send_request("getBlock", [slot, config])
        if self.clean_response:
            if response is None:
                return None
            if encoding not in (
                None,
                "json",
                "jsonParsed",
            ) or transaction_details not in (
                None,
                "full",
            ):
                return response
            return Block(response)
        return response

    def get_block_height(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        """Returns the current block height."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return self.build_and_send_request("getBlockHeight", [config] if config else [])

    def get_block_production(
        self,
        commitment: Commitment | None = None,
        identity: PublicKey | str | None = None,
        first_slot: int | None = None,
        last_slot: int | None = None,
    ) -> RPCResponse[BlockProductionType] | BlockProduction:
        """Returns recent block production information."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if identity is not None:
            config["identity"] = str(identity)
        if first_slot is not None or last_slot is not None:
            range_: dict[str, int] = {}
            if first_slot is not None:
                range_["firstSlot"] = first_slot
            if last_slot is not None:
                range_["lastSlot"] = last_slot
            config["range"] = range_
        response = self.build_and_send_request(
            "getBlockProduction", [config] if config else []
        )
        if self.clean_response:
            production = BlockProduction(response["value"])
            production.context = response.get("context")
            return production
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
        self,
        start_slot: int,
        end_slot: int | None = None,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[int]] | list[int]:
        """Returns a list of confirmed blocks between two slots."""
        params: list = [start_slot]
        if end_slot is not None:
            params.append(end_slot)
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            if end_slot is None:
                params.append(None)
            params.append(config)
        return self.build_and_send_request("getBlocks", params)

    def get_blocks_with_limit(
        self,
        start_slot: int,
        limit: int,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[int]] | list[int]:
        """Returns a list of confirmed blocks starting at the given slot."""
        if not 1 <= limit <= 500_000:
            raise ValueError("limit must be between 1 and 500000")
        params: list[Any] = [start_slot, limit]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        return self.build_and_send_request("getBlocksWithLimit", params)

    def get_block_time(self, block: int) -> RPCResponse[int | None] | int | None:
        """Returns the estimated production time of a block."""
        return self.build_and_send_request("getBlockTime", [block])

    def get_latest_blockhash(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[BlockHashType] | BlockHash:
        """Returns the latest blockhash."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = self.build_and_send_request(
            "getLatestBlockhash", [config] if config else []
        )
        if self.clean_response:
            blockhash = BlockHash(response["value"])
            blockhash.context = response.get("context")
            return blockhash
        return response

    def is_blockhash_valid(
        self,
        blockhash: str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[bool] | bool:
        """Returns whether a blockhash is still valid."""
        params: list = [blockhash]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("isBlockhashValid", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Cluster Methods
    # ========================================================================

    def get_cluster_nodes(
        self,
    ) -> RPCResponse[list[ClusterNodeType]] | list[ClusterNode]:
        """Returns information about all nodes participating in the cluster."""
        response = self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(node) for node in response]
        return response

    def get_epoch_info(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[EpochType] | Epoch:
        """Returns information about the current epoch."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = self.build_and_send_request(
            "getEpochInfo", [config] if config else []
        )
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

    def get_version(self) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        """Returns the current Solana version running on the node."""
        return self.build_and_send_request("getVersion", [None])

    def get_highest_snapshot_slot(self) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        """Returns the highest slot info that the node has snapshots for."""
        return self.build_and_send_request("getHighestSnapshotSlot", [None])

    def get_leader_schedule(
        self,
        slot: int | None = None,
        commitment: Commitment | None = None,
        identity: PublicKey | str | None = None,
    ) -> RPCResponse[dict[str, list[int]]] | dict[str, list[int]]:
        """Returns the leader schedule for an epoch."""
        params: list[Any] = [slot]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if identity is not None:
            config["identity"] = str(identity)
        if config:
            params.append(config)
        return self.build_and_send_request("getLeaderSchedule", params)

    def get_max_retransmit_slot(self) -> RPCResponse[int] | int:
        """Returns the max slot seen from retransmit stage."""
        return self.build_and_send_request("getMaxRetransmitSlot", [None])

    def get_max_shred_insert_slot(self) -> RPCResponse[int] | int:
        """Returns the max slot seen from after shred insert."""
        return self.build_and_send_request("getMaxShredInsertSlot", [None])

    def get_slot(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int | None] | int | None:
        """Returns the current slot."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return self.build_and_send_request("getSlot", [config] if config else [])

    def get_slot_leader(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[str] | str:
        """Returns the current slot leader."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return self.build_and_send_request("getSlotLeader", [config] if config else [])

    def get_slot_leaders(
        self, start_slot: int, limit: int
    ) -> RPCResponse[list[str]] | list[str]:
        """Returns the slot leaders for a given slot range."""
        if not 1 <= limit <= 5_000:
            raise ValueError("limit must be between 1 and 5000")
        return self.build_and_send_request("getSlotLeaders", [start_slot, limit])

    def minimum_ledger_slot(self) -> RPCResponse[int] | int:
        """Returns the lowest slot that the node has info about in its ledger."""
        return self.build_and_send_request("minimumLedgerSlot", [None])

    def get_vote_accounts(
        self,
        commitment: Commitment | None = None,
        vote_public_key: PublicKey | str | None = None,
        keep_unstaked_delinquents: bool | None = None,
        delinquent_slot_distance: int | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        """Returns the account info and associated stake for all voting accounts."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if vote_public_key is not None:
            config["votePubkey"] = str(vote_public_key)
        if keep_unstaked_delinquents is not None:
            config["keepUnstakedDelinquents"] = keep_unstaked_delinquents
        if delinquent_slot_distance is not None:
            config["delinquentSlotDistance"] = delinquent_slot_distance
        return self.build_and_send_request(
            "getVoteAccounts", [config] if config else []
        )

    # ========================================================================
    # Fee Methods
    # ========================================================================

    def get_fee_for_message(
        self,
        message: str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int | None] | int | None:
        """Returns the fee for a given message (base64-encoded)."""
        params: list = [message]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getFeeForMessage", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_recent_prioritization_fees(
        self, addresses: list[str] | None = None
    ) -> RPCResponse[list[dict[str, Any]]] | list[dict[str, Any]]:
        """Returns recent prioritization fees from recent blocks."""
        if addresses is not None and len(addresses) > 128:
            raise ValueError("addresses cannot contain more than 128 entries")
        params: list = []
        if addresses:
            params.append(addresses)
        return self.build_and_send_request(
            "getRecentPrioritizationFees", params if params else [None]
        )

    # ========================================================================
    # Inflation Methods
    # ========================================================================

    def get_inflation_governor(
        self, commitment: Commitment | None = None
    ) -> RPCResponse[InflationGovernorType] | InflationGovernor:
        """Returns the current inflation governor."""
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request(
            "getInflationGovernor", params if params else [None]
        )
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
        self,
        addresses: list[str],
        commitment: Commitment | None = None,
        epoch: int | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[InflationRewardType | None]] | list[InflationReward | None]:
        """Returns the inflation / staking reward for a list of addresses."""
        if not 1 <= len(addresses) <= 100:
            raise ValueError("addresses must contain between 1 and 100 entries")
        params: list = [addresses]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if epoch is not None:
            config["epoch"] = epoch
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getInflationReward", params)
        if self.clean_response:
            return [
                InflationReward(reward) if reward is not None else None
                for reward in response
            ]
        return response

    # ========================================================================
    # Supply Methods
    # ========================================================================

    def get_supply(
        self,
        commitment: Commitment | None = None,
        exclude_non_circulating_accounts_list: bool = False,
    ) -> RPCResponse[SupplyType] | Supply:
        """Returns information about the current supply."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        config["excludeNonCirculatingAccountsList"] = (
            exclude_non_circulating_accounts_list
        )
        response = self.build_and_send_request("getSupply", [config] if config else [])
        if self.clean_response:
            supply = Supply(response["value"])
            supply.context = response.get("context")
            return supply
        return response

    # ========================================================================
    # Stake Methods
    # ========================================================================

    def get_stake_minimum_delegation(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        """Returns the stake minimum delegation in lamports."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = self.build_and_send_request(
            "getStakeMinimumDelegation", [config] if config else []
        )
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Token Methods
    # ========================================================================

    def get_token_accounts_by_owner(
        self,
        public_key: str | PublicKey,
        commitment: Commitment | None = None,
        *,
        mint_id: str | PublicKey | None = None,
        program_id: str | PublicKey | None = None,
        encoding: str = "jsonParsed",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[ProgramAccountType]] | list[ProgramAccount]:
        """Returns all SPL Token accounts by owner."""
        if (mint_id is None) == (program_id is None):
            raise ValueError("Pass exactly one of mint_id or program_id")

        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot

        response = self.build_and_send_request(
            "getTokenAccountsByOwner",
            [
                str(public_key),
                {"mint": str(mint_id)}
                if mint_id is not None
                else {"programId": str(program_id)},
                config,
            ],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_token_accounts_by_delegate(
        self,
        delegate: str | PublicKey,
        commitment: Commitment | None = None,
        *,
        mint_id: str | PublicKey | None = None,
        program_id: str | PublicKey | None = None,
        encoding: str = "jsonParsed",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[ProgramAccountType]] | list[ProgramAccount]:
        """Returns all SPL Token accounts approved by a delegate."""
        if (mint_id is None) == (program_id is None):
            raise ValueError("Pass exactly one of mint_id or program_id")

        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot

        response = self.build_and_send_request(
            "getTokenAccountsByDelegate",
            [
                str(delegate),
                {"mint": str(mint_id)}
                if mint_id is not None
                else {"programId": str(program_id)},
                config,
            ],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_all_token_accounts_by_owner(
        self,
        public_key: str | PublicKey,
        commitment: Commitment | None = None,
        encoding: str = "jsonParsed",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> list[ProgramAccount] | list[RPCResponse]:
        """Return owner accounts from both Token and Token-2022 in one batch."""
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot

        responses = self.send_batch(
            [
                (
                    "getTokenAccountsByOwner",
                    [str(public_key), {"programId": str(program_id)}, config],
                )
                for program_id in token_program_ids()
            ]
        )
        if not self.clean_response:
            return responses
        return [
            ProgramAccount(account)
            for result in responses
            for account in result["value"]
        ]

    def get_token_account_balance(
        self,
        token_account: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse:
        """Returns the token balance of an SPL Token account."""
        params: list = [str(token_account)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getTokenAccountBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_token_supply(
        self,
        mint: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        """Returns the total supply of an SPL Token."""
        params: list = [str(mint)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getTokenSupply", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_token_largest_accounts(
        self,
        mint: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[dict[str, Any]]] | list[dict[str, Any]]:
        """Returns the 20 largest accounts for an SPL Token."""
        params: list = [str(mint)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = self.build_and_send_request("getTokenLargestAccounts", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Transaction Methods
    # ========================================================================

    def get_transaction(
        self,
        signature: str,
        commitment: Commitment | None = None,
        max_supported_transaction_version: int | None = 0,
        encoding: str = "json",
    ) -> (
        RPCResponse[TransactionElementType | None]
        | TransactionElement
        | dict[str, Any]
        | None
    ):
        """Returns transaction details for a confirmed transaction."""
        config: dict[str, Any] = {"encoding": encoding}
        if max_supported_transaction_version is not None:
            config["maxSupportedTransactionVersion"] = max_supported_transaction_version
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getTransaction", [signature, config])
        if self.clean_response:
            if response is None:
                return None
            if encoding not in ("json", "jsonParsed"):
                return response
            return TransactionElement(response)
        return response

    def get_transaction_count(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        """Returns the current transaction count from the ledger."""
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return self.build_and_send_request(
            "getTransactionCount", [config] if config else []
        )

    def get_signatures_for_address(
        self,
        acct_address: str,
        limit: int | None = None,
        before: str | None = None,
        until: str | None = None,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[TransactionSignatureType]] | list[TransactionSignature]:
        """Returns signatures for confirmed transactions involving an address."""
        if limit is not None and not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        params: list = [acct_address]
        options: dict[str, Any] = {}
        if limit is not None:
            options["limit"] = limit
        if before is not None:
            options["before"] = before
        if until is not None:
            options["until"] = until
        if commitment:
            options.update(validate_commitment(commitment))
        if min_context_slot is not None:
            options["minContextSlot"] = min_context_slot
        if options:
            params.append(options)
        response = self.build_and_send_request("getSignaturesForAddress", params)
        if self.clean_response:
            return [TransactionSignature(sig) for sig in response]
        return response

    def get_signature_statuses(
        self, transaction_sigs: list[str], search_transaction_history: bool = False
    ) -> RPCResponse[list[SignatureStatusType | None]] | list[SignatureStatus | None]:
        """Returns the statuses of a list of signatures."""
        if not 1 <= len(transaction_sigs) <= 256:
            raise ValueError(
                "transaction_sigs must contain between 1 and 256 signatures"
            )
        params: list = [transaction_sigs]
        if search_transaction_history:
            params.append({"searchTransactionHistory": True})
        response = self.build_and_send_request("getSignatureStatuses", params)
        if self.clean_response:
            return [
                SignatureStatus(status) if status is not None else None
                for status in response["value"]
            ]
        return response

    def confirm_transaction(
        self,
        signature: str,
        commitment: Commitment = "finalized",
        last_valid_block_height: int | None = None,
        timeout: float | None = 30.0,
        poll_interval: float = 0.5,
    ) -> dict[str, Any]:
        """Wait until a signature reaches commitment or its blockhash expires."""
        validate_commitment(commitment)
        validate_confirmation_polling(timeout, poll_interval)
        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            statuses = self.get_signature_statuses(
                [signature], search_transaction_history=True
            )
            status = signature_status_payload(statuses, self.clean_response)
            if status is not None:
                if status.get("err") is not None:
                    raise RPCRequestError(
                        f"Transaction {signature} failed",
                        data=status["err"],
                    )
                if commitment_reached(status, commitment):
                    return status

            if last_valid_block_height is not None:
                block_height = block_height_value(
                    self.get_block_height(commitment), self.clean_response
                )
                if block_height > last_valid_block_height:
                    raise RPCRequestError(
                        f"Transaction {signature} expired before confirmation",
                        data={
                            "blockHeight": block_height,
                            "lastValidBlockHeight": last_valid_block_height,
                        },
                    )

            if deadline is not None and time.monotonic() >= deadline:
                raise RPCRequestError(
                    f"Transaction {signature} was not confirmed before timeout"
                )
            time.sleep(poll_interval)

    def get_recent_performance_samples(
        self, limit: int | None = None
    ) -> (
        RPCResponse[list[RecentPerformanceSamplesType]] | list[RecentPerformanceSamples]
    ):
        """Returns a list of recent performance samples."""
        if limit is not None and not 1 <= limit <= 720:
            raise ValueError("limit must be between 1 and 720")
        params: list = [limit] if limit is not None else [None]
        response = self.build_and_send_request("getRecentPerformanceSamples", params)
        if self.clean_response:
            return [RecentPerformanceSamples(sample) for sample in response]
        return response

    def simulate_transaction(
        self,
        transaction: str | bytes | Transaction | VersionedTransaction,
        sig_verify: bool = False,
        commitment: Commitment | None = None,
        replace_recent_blockhash: bool = False,
        min_context_slot: int | None = None,
        inner_instructions: bool = False,
        accounts: dict[str, Any] | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        """Simulates sending a transaction (base64-encoded)."""
        if sig_verify and replace_recent_blockhash:
            raise ValueError(
                "sig_verify and replace_recent_blockhash cannot both be enabled"
            )
        config: dict[str, Any] = {
            "encoding": "base64",
            "sigVerify": sig_verify,
            "replaceRecentBlockhash": replace_recent_blockhash,
            "innerInstructions": inner_instructions,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if accounts is not None:
            config["accounts"] = accounts
        if isinstance(transaction, (Transaction, VersionedTransaction)):
            if (
                isinstance(transaction, Transaction)
                and transaction.recent_blockhash is None
                and transaction.nonce_info is None
            ):
                if replace_recent_blockhash:
                    transaction.recent_blockhash = DEFAULT_BLOCKHASH
                else:
                    latest = self.get_latest_blockhash()
                    transaction.recent_blockhash = latest_blockhash_value(
                        latest, self.clean_response
                    )[0]
            if sig_verify:
                transaction.sign()
            if isinstance(transaction, Transaction):
                transaction = transaction.serialize(
                    require_all_signatures=sig_verify,
                    verify_signatures=sig_verify,
                )
            else:
                transaction = transaction.serialize(require_all_signatures=sig_verify)
        response = self.build_and_send_request(
            "simulateTransaction",
            [transaction, config],
        )
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Action Methods (non-get)
    # ========================================================================

    def request_airdrop(
        self,
        public_key: PublicKey | str,
        lamports: int,
        commitment: Commitment | None = None,
        recent_blockhash: str | None = None,
    ) -> RPCResponse[str] | str:
        """Requests an airdrop of lamports to the specified public key."""
        params: list = [str(public_key), lamports]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if recent_blockhash is not None:
            config["recentBlockhash"] = recent_blockhash
        if config:
            params.append(config)
        return self.build_and_send_request("requestAirdrop", params)

    def send_transaction(
        self,
        transaction: Transaction | VersionedTransaction,
        options: dict | None = None,
    ) -> RPCResponse[str] | str:
        """Signs and sends a transaction to the network."""
        recent_blockhash = transaction.recent_blockhash
        if (
            isinstance(transaction, Transaction)
            and recent_blockhash is None
            and transaction.nonce_info is None
        ):
            blockhash_resp = self.get_latest_blockhash()
            recent_blockhash = latest_blockhash_value(
                blockhash_resp, self.clean_response
            )[0]

        if options is None:
            options = {"encoding": "base64"}

        if isinstance(transaction, Transaction):
            transaction.recent_blockhash = recent_blockhash
        transaction.sign()
        return self.send_raw_transaction(transaction.serialize(), options)

    def send_and_confirm_transaction(
        self,
        transaction: Transaction | VersionedTransaction,
        options: dict | None = None,
        commitment: Commitment = "finalized",
        last_valid_block_height: int | None = None,
        timeout: float | None = None,
        poll_interval: float = 0.5,
    ) -> str:
        """Sign and send once, then wait for confirmation or expiration.

        Durable-nonce transactions do not have a last-valid block height, so
        callers must give them a finite timeout. Other pre-blockhashed
        transactions must provide the matching ``last_valid_block_height``.
        """
        fetched_min_context_slot: int | None = None
        uses_durable_nonce = (
            isinstance(transaction, Transaction) and transaction.nonce_info is not None
        )
        if uses_durable_nonce:
            if last_valid_block_height is not None:
                raise ValueError(
                    "last_valid_block_height does not apply to durable-nonce "
                    "transactions"
                )
            if timeout is None:
                raise ValueError(
                    "A finite timeout is required for durable-nonce transactions"
                )
        elif (
            isinstance(transaction, Transaction)
            and transaction.recent_blockhash is None
        ):
            latest = self.get_latest_blockhash(commitment)
            blockhash, fetched_last_valid_height = latest_blockhash_value(
                latest, self.clean_response
            )
            transaction.recent_blockhash = blockhash
            fetched_min_context_slot = response_context_slot(
                latest, self.clean_response
            )
            if last_valid_block_height is None:
                last_valid_block_height = fetched_last_valid_height
            if last_valid_block_height is None:
                raise RPCRequestError(
                    "getLatestBlockhash did not return lastValidBlockHeight"
                )
        elif last_valid_block_height is None:
            raise ValueError(
                "last_valid_block_height is required when the transaction "
                "already has a recent blockhash"
            )

        transaction.sign()
        serialized = transaction.serialize()
        send_options: dict[str, Any] = {"preflightCommitment": commitment}
        if fetched_min_context_slot is not None:
            send_options["minContextSlot"] = fetched_min_context_slot
        send_options = {
            key: value for key, value in send_options.items() if value is not None
        }
        send_options.update(options or {})
        response = self.send_raw_transaction(serialized, send_options)
        signature = transaction_signature_value(response, self.clean_response)
        self.confirm_transaction(
            signature,
            commitment=commitment,
            last_valid_block_height=last_valid_block_height,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        return signature

    def send_raw_transaction(
        self,
        transaction: bytes,
        options: dict | None = None,
    ) -> RPCResponse[str] | str:
        options = {"encoding": "base64", **(options or {})}
        if options["encoding"] != "base64":
            raise ValueError("Raw transaction bytes require base64 encoding")
        return self.build_and_send_request(
            "sendTransaction",
            [transaction, options],
        )

    # ========================================================================
    # Internal
    # ========================================================================

    def build_and_send_request(
        self, method: str, params: list[Any] | None = None
    ) -> Any:
        """Builds and sends an RPC request."""
        data: dict[str, Any] = self.http.build_data(method=method, params=params)
        res: RPCResponse = self.http.send(data)
        return unwrap_rpc_envelope(res) if self.clean_response else res

    def send_batch(
        self,
        requests: list[tuple[str, list[Any] | None]],
    ) -> list[Any]:
        batch = [
            self.http.build_data(method=method, params=params)
            for method, params in requests
        ]
        responses = self.http.send_batch(batch)
        responses_by_id = {response["id"]: response for response in responses}
        ordered = [responses_by_id[request["id"]] for request in batch]
        if self.clean_response:
            return [unwrap_rpc_envelope(response) for response in ordered]
        return ordered
