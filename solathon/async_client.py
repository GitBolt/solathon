from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

import httpx

from .core.http import AsyncHTTPClient
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


class AsyncClient:
    def __init__(
        self,
        endpoint: str,
        local: bool = False,
        clean_response: bool = True,
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """
        Async Solana RPC client.

        Args:
            endpoint (str): The RPC endpoint URL.
            local (bool): Skip endpoint validation. Defaults to False.
            clean_response (bool): Whether to unwrap RPC responses. Defaults to True.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL.")
        self.http = AsyncHTTPClient(endpoint, timeout=timeout, client=http_client)
        self.endpoint = endpoint
        self.clean_response = clean_response

    async def refresh_http(self) -> None:
        await self.http.refresh()

    async def close(self) -> None:
        await self.http.close()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ========================================================================
    # Account Methods
    # ========================================================================

    async def get_account_info(
        self,
        public_key: PublicKey | str,
        commitment: Commitment | None = None,
        encoding: str = "base64",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[AccountInfoType] | AccountInfo:
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
            "getAccountInfo", [str(public_key), config]
        )
        if self.clean_response:
            if response["value"] is None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            account = AccountInfo(response["value"])
            account.context = response.get("context")
            return account
        return response

    async def get_balance(
        self,
        public_key: PublicKey | str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        params: list = [str(public_key)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("getBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_multiple_accounts(
        self,
        pubkeys: list[PublicKey | str],
        commitment: Commitment | None = None,
        encoding: str = "base64",
        data_slice: dict[str, int] | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[AccountInfoType | None]] | list[AccountInfo | None]:
        if not 1 <= len(pubkeys) <= 100:
            raise ValueError("pubkeys must contain between 1 and 100 addresses")
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
            "getMultipleAccounts", [[str(pubkey) for pubkey in pubkeys], config]
        )
        if self.clean_response:
            return [
                AccountInfo(account) if account is not None else None
                for account in response["value"]
            ]
        return response

    async def get_program_accounts(
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
        response = await self.build_and_send_request(
            "getProgramAccounts", [str(public_key), config]
        )
        if self.clean_response:
            if with_context:
                return response
            return [ProgramAccount(a) for a in response]
        return response

    async def get_largest_accounts(
        self,
        commitment: Commitment | None = None,
        filter: Literal["circulating", "nonCirculating"] | None = None,
        sort_results: bool | None = None,
    ) -> RPCResponse[list[LargestAccountsType]] | list[LargestAccounts]:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if filter:
            config["filter"] = filter
        if sort_results is not None:
            config["sortResults"] = sort_results
        response = await self.build_and_send_request(
            "getLargestAccounts",
            [config] if config else [None],
        )
        if self.clean_response:
            return [LargestAccounts(a) for a in response["value"]]
        return response

    async def get_minimum_balance_for_rent_exemption(
        self,
        acct_length: int | None = None,
        commitment: Commitment | None = None,
        *,
        data_length: int | None = None,
    ) -> RPCResponse[int] | int:
        if acct_length is None:
            acct_length = data_length
        elif data_length is not None:
            raise TypeError("Pass acct_length or data_length, not both")
        if acct_length is None:
            raise TypeError("acct_length is required")
        params: list = [acct_length]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request(
            "getMinimumBalanceForRentExemption", params
        )

    # ========================================================================
    # Block Methods
    # ========================================================================

    async def get_block(
        self,
        slot: int,
        commitment: Commitment | None = None,
        max_supported_transaction_version: int | None = 0,
        encoding: str | None = None,
        transaction_details: Literal["full", "accounts", "signatures", "none"]
        | None = None,
        rewards: bool | None = None,
    ) -> RPCResponse[BlockType] | Block | dict[str, Any] | None:
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
        response = await self.build_and_send_request("getBlock", [slot, config])
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

    async def get_block_height(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return await self.build_and_send_request(
            "getBlockHeight", [config] if config else []
        )

    async def get_block_production(
        self,
        commitment: Commitment | None = None,
        identity: PublicKey | str | None = None,
        first_slot: int | None = None,
        last_slot: int | None = None,
    ) -> RPCResponse[BlockProductionType] | BlockProduction:
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
        response = await self.build_and_send_request(
            "getBlockProduction", [config] if config else []
        )
        if self.clean_response:
            production = BlockProduction(response["value"])
            production.context = response.get("context")
            return production
        return response

    async def get_block_commitment(
        self, block: int
    ) -> RPCResponse[BlockCommitmentType] | BlockCommitment:
        response = await self.build_and_send_request("getBlockCommitment", [block])
        if self.clean_response:
            return BlockCommitment(response)
        return response

    async def get_blocks(
        self,
        start_slot: int,
        end_slot: int | None = None,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[int]] | list[int]:
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
        return await self.build_and_send_request("getBlocks", params)

    async def get_blocks_with_limit(
        self,
        start_slot: int,
        limit: int,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[int]] | list[int]:
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
        return await self.build_and_send_request("getBlocksWithLimit", params)

    async def get_block_time(self, block: int) -> RPCResponse[int | None] | int | None:
        return await self.build_and_send_request("getBlockTime", [block])

    async def get_latest_blockhash(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[BlockHashType] | BlockHash:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
            "getLatestBlockhash", [config] if config else []
        )
        if self.clean_response:
            blockhash = BlockHash(response["value"])
            blockhash.context = response.get("context")
            return blockhash
        return response

    async def is_blockhash_valid(
        self,
        blockhash: str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[bool] | bool:
        params: list = [blockhash]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("isBlockhashValid", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Cluster Methods
    # ========================================================================

    async def get_cluster_nodes(
        self,
    ) -> RPCResponse[list[ClusterNodeType]] | list[ClusterNode]:
        response = await self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(n) for n in response]
        return response

    async def get_epoch_info(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[EpochType] | Epoch:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
            "getEpochInfo", [config] if config else []
        )
        if self.clean_response:
            return Epoch(response)
        return response

    async def get_epoch_schedule(
        self,
    ) -> RPCResponse[EpochScheduleType] | EpochSchedule:
        response = await self.build_and_send_request("getEpochSchedule", [None])
        if self.clean_response:
            return EpochSchedule(response)
        return response

    async def get_first_available_block(self) -> RPCResponse[int] | int:
        return await self.build_and_send_request("getFirstAvailableBlock", [None])

    async def get_genesis_hash(self) -> RPCResponse[str] | str:
        return await self.build_and_send_request("getGenesisHash", [None])

    async def get_health(self) -> RPCResponse[Literal["ok"]] | Literal["ok"]:
        return await self.build_and_send_request("getHealth", [None])

    async def get_identity(
        self,
    ) -> RPCResponse[PubKeyIdentityType] | PubKeyIdentity:
        response = await self.build_and_send_request("getIdentity", [None])
        if self.clean_response:
            return PubKeyIdentity(response)
        return response

    async def get_version(self) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        return await self.build_and_send_request("getVersion", [None])

    async def get_highest_snapshot_slot(
        self,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        return await self.build_and_send_request("getHighestSnapshotSlot", [None])

    async def get_leader_schedule(
        self,
        slot: int | None = None,
        commitment: Commitment | None = None,
        identity: PublicKey | str | None = None,
    ) -> RPCResponse[dict[str, list[int]]] | dict[str, list[int]]:
        params: list[Any] = [slot]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if identity is not None:
            config["identity"] = str(identity)
        if config:
            params.append(config)
        return await self.build_and_send_request("getLeaderSchedule", params)

    async def get_max_retransmit_slot(self) -> RPCResponse[int] | int:
        return await self.build_and_send_request("getMaxRetransmitSlot", [None])

    async def get_max_shred_insert_slot(self) -> RPCResponse[int] | int:
        return await self.build_and_send_request("getMaxShredInsertSlot", [None])

    async def get_slot(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int | None] | int | None:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return await self.build_and_send_request("getSlot", [config] if config else [])

    async def get_slot_leader(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[str] | str:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return await self.build_and_send_request(
            "getSlotLeader", [config] if config else []
        )

    async def get_slot_leaders(
        self, start_slot: int, limit: int
    ) -> RPCResponse[list[str]] | list[str]:
        if not 1 <= limit <= 5_000:
            raise ValueError("limit must be between 1 and 5000")
        return await self.build_and_send_request("getSlotLeaders", [start_slot, limit])

    async def minimum_ledger_slot(self) -> RPCResponse[int] | int:
        return await self.build_and_send_request("minimumLedgerSlot", [None])

    async def get_vote_accounts(
        self,
        commitment: Commitment | None = None,
        vote_public_key: PublicKey | str | None = None,
        keep_unstaked_delinquents: bool | None = None,
        delinquent_slot_distance: int | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if vote_public_key is not None:
            config["votePubkey"] = str(vote_public_key)
        if keep_unstaked_delinquents is not None:
            config["keepUnstakedDelinquents"] = keep_unstaked_delinquents
        if delinquent_slot_distance is not None:
            config["delinquentSlotDistance"] = delinquent_slot_distance
        return await self.build_and_send_request(
            "getVoteAccounts", [config] if config else []
        )

    # ========================================================================
    # Fee Methods
    # ========================================================================

    async def get_fee_for_message(
        self,
        message: str,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int | None] | int | None:
        params: list = [message]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("getFeeForMessage", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_recent_prioritization_fees(
        self, addresses: list[str] | None = None
    ) -> RPCResponse[list[dict[str, Any]]] | list[dict[str, Any]]:
        if addresses is not None and len(addresses) > 128:
            raise ValueError("addresses cannot contain more than 128 entries")
        params: list = []
        if addresses:
            params.append(addresses)
        return await self.build_and_send_request(
            "getRecentPrioritizationFees", params if params else [None]
        )

    # ========================================================================
    # Inflation Methods
    # ========================================================================

    async def get_inflation_governor(
        self, commitment: Commitment | None = None
    ) -> RPCResponse[InflationGovernorType] | InflationGovernor:
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request(
            "getInflationGovernor", params if params else [None]
        )
        if self.clean_response:
            return InflationGovernor(response)
        return response

    async def get_inflation_rate(
        self,
    ) -> RPCResponse[InflationRateType] | InflationRate:
        response = await self.build_and_send_request("getInflationRate", [None])
        if self.clean_response:
            return InflationRate(response)
        return response

    async def get_inflation_reward(
        self,
        addresses: list[str],
        commitment: Commitment | None = None,
        epoch: int | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[InflationRewardType | None]] | list[InflationReward | None]:
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
        response = await self.build_and_send_request("getInflationReward", params)
        if self.clean_response:
            return [
                InflationReward(reward) if reward is not None else None
                for reward in response
            ]
        return response

    # ========================================================================
    # Supply / Stake
    # ========================================================================

    async def get_supply(
        self,
        commitment: Commitment | None = None,
        exclude_non_circulating_accounts_list: bool = False,
    ) -> RPCResponse[SupplyType] | Supply:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        config["excludeNonCirculatingAccountsList"] = (
            exclude_non_circulating_accounts_list
        )
        response = await self.build_and_send_request(
            "getSupply", [config] if config else []
        )
        if self.clean_response:
            supply = Supply(response["value"])
            supply.context = response.get("context")
            return supply
        return response

    async def get_stake_minimum_delegation(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
            "getStakeMinimumDelegation", [config] if config else []
        )
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Token Methods
    # ========================================================================

    async def get_token_accounts_by_owner(
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
        if (mint_id is None) == (program_id is None):
            raise ValueError("Pass exactly one of mint_id or program_id")
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
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
            return [ProgramAccount(a) for a in response["value"]]
        return response

    async def get_token_accounts_by_delegate(
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
        if (mint_id is None) == (program_id is None):
            raise ValueError("Pass exactly one of mint_id or program_id")
        config: dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if data_slice is not None:
            config["dataSlice"] = data_slice
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        response = await self.build_and_send_request(
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
            return [ProgramAccount(a) for a in response["value"]]
        return response

    async def get_all_token_accounts_by_owner(
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

        responses = await self.send_batch(
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

    async def get_token_account_balance(
        self,
        token_account: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse:
        params: list = [str(token_account)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("getTokenAccountBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_token_supply(
        self,
        mint: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
        params: list = [str(mint)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("getTokenSupply", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_token_largest_accounts(
        self,
        mint: str | PublicKey,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[dict[str, Any]]] | list[dict[str, Any]]:
        params: list = [str(mint)]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        if config:
            params.append(config)
        response = await self.build_and_send_request("getTokenLargestAccounts", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Transaction Methods
    # ========================================================================

    async def get_transaction(
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
        config: dict[str, Any] = {"encoding": encoding}
        if max_supported_transaction_version is not None:
            config["maxSupportedTransactionVersion"] = max_supported_transaction_version
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request(
            "getTransaction", [signature, config]
        )
        if self.clean_response:
            if response is None:
                return None
            if encoding not in ("json", "jsonParsed"):
                return response
            return TransactionElement(response)
        return response

    async def get_transaction_count(
        self,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[int] | int:
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if min_context_slot is not None:
            config["minContextSlot"] = min_context_slot
        return await self.build_and_send_request(
            "getTransactionCount", [config] if config else []
        )

    async def get_signatures_for_address(
        self,
        acct_address: str,
        limit: int | None = None,
        before: str | None = None,
        until: str | None = None,
        commitment: Commitment | None = None,
        min_context_slot: int | None = None,
    ) -> RPCResponse[list[TransactionSignatureType]] | list[TransactionSignature]:
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
        response = await self.build_and_send_request("getSignaturesForAddress", params)
        if self.clean_response:
            return [TransactionSignature(s) for s in response]
        return response

    async def get_signature_statuses(
        self, transaction_sigs: list[str], search_transaction_history: bool = False
    ) -> RPCResponse[list[SignatureStatusType | None]] | list[SignatureStatus | None]:
        if not 1 <= len(transaction_sigs) <= 256:
            raise ValueError(
                "transaction_sigs must contain between 1 and 256 signatures"
            )
        params: list = [transaction_sigs]
        if search_transaction_history:
            params.append({"searchTransactionHistory": True})
        response = await self.build_and_send_request("getSignatureStatuses", params)
        if self.clean_response:
            return [
                SignatureStatus(status) if status is not None else None
                for status in response["value"]
            ]
        return response

    async def confirm_transaction(
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
            statuses = await self.get_signature_statuses(
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
                    await self.get_block_height(commitment), self.clean_response
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
            await asyncio.sleep(poll_interval)

    async def get_recent_performance_samples(
        self, limit: int | None = None
    ) -> (
        RPCResponse[list[RecentPerformanceSamplesType]] | list[RecentPerformanceSamples]
    ):
        if limit is not None and not 1 <= limit <= 720:
            raise ValueError("limit must be between 1 and 720")
        params: list = [limit] if limit is not None else [None]
        response = await self.build_and_send_request(
            "getRecentPerformanceSamples", params
        )
        if self.clean_response:
            return [RecentPerformanceSamples(s) for s in response]
        return response

    async def simulate_transaction(
        self,
        transaction: str | bytes | Transaction | VersionedTransaction,
        sig_verify: bool = False,
        commitment: Commitment | None = None,
        replace_recent_blockhash: bool = False,
        min_context_slot: int | None = None,
        inner_instructions: bool = False,
        accounts: dict[str, Any] | None = None,
    ) -> RPCResponse[dict[str, Any]] | dict[str, Any]:
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
                    latest = await self.get_latest_blockhash()
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
        response = await self.build_and_send_request(
            "simulateTransaction",
            [transaction, config],
        )
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Action Methods
    # ========================================================================

    async def request_airdrop(
        self,
        public_key: PublicKey | str,
        lamports: int,
        commitment: Commitment | None = None,
        recent_blockhash: str | None = None,
    ) -> RPCResponse[str] | str:
        params: list = [str(public_key), lamports]
        config: dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if recent_blockhash is not None:
            config["recentBlockhash"] = recent_blockhash
        if config:
            params.append(config)
        return await self.build_and_send_request("requestAirdrop", params)

    async def send_transaction(
        self,
        transaction: Transaction | VersionedTransaction,
        options: dict | None = None,
    ) -> RPCResponse[str] | str:
        recent_blockhash = transaction.recent_blockhash
        if (
            isinstance(transaction, Transaction)
            and recent_blockhash is None
            and transaction.nonce_info is None
        ):
            blockhash_resp = await self.get_latest_blockhash()
            recent_blockhash = latest_blockhash_value(
                blockhash_resp, self.clean_response
            )[0]

        if options is None:
            options = {"encoding": "base64"}

        if isinstance(transaction, Transaction):
            transaction.recent_blockhash = recent_blockhash
        transaction.sign()
        return await self.send_raw_transaction(transaction.serialize(), options)

    async def send_and_confirm_transaction(
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
            latest = await self.get_latest_blockhash(commitment)
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
        response = await self.send_raw_transaction(serialized, send_options)
        signature = transaction_signature_value(response, self.clean_response)
        await self.confirm_transaction(
            signature,
            commitment=commitment,
            last_valid_block_height=last_valid_block_height,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        return signature

    async def send_raw_transaction(
        self,
        transaction: bytes,
        options: dict | None = None,
    ) -> RPCResponse[str] | str:
        options = {"encoding": "base64", **(options or {})}
        if options["encoding"] != "base64":
            raise ValueError("Raw transaction bytes require base64 encoding")
        return await self.build_and_send_request(
            "sendTransaction",
            [transaction, options],
        )

    # ========================================================================
    # Internal
    # ========================================================================

    async def build_and_send_request(
        self, method: str, params: list[Any] | None = None
    ) -> Any:
        """Compatibility spelling; delegates to the original async API name."""
        return await self.build_and_send_request_async(method, params)

    async def build_and_send_request_async(
        self, method: str, params: list[Any] | None = None
    ) -> Any:
        """Build and send one JSON-RPC request."""
        data: dict[str, Any] = self.http.build_data(method=method, params=params)
        res = await self.http.send(data)
        return unwrap_rpc_envelope(res) if self.clean_response else res

    async def send_batch(
        self,
        requests: list[tuple[str, list[Any] | None]],
    ) -> list[Any]:
        batch = [
            self.http.build_data(method=method, params=params)
            for method, params in requests
        ]
        responses = await self.http.send_batch(batch)
        responses_by_id = {response["id"]: response for response in responses}
        ordered = [responses_by_id[request["id"]] for request in batch]
        if self.clean_response:
            return [unwrap_rpc_envelope(response) for response in ordered]
        return ordered
