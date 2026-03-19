from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Text, Union

from .utils import RPCRequestError, validate_commitment
from .publickey import PublicKey
from .core.http import AsyncHTTPClient
from .transaction import Transaction
from .core.types import (
    Commitment,
    RPCResponse,
    AccountInfo,
    Block,
    BlockProduction,
    BlockCommitment,
    BlockHash,
    ClusterNode,
    Epoch,
    EpochSchedule,
    InflationGovernor,
    InflationRate,
    InflationReward,
    LargestAccounts,
    ProgramAccount,
    PubKeyIdentity,
    RecentPerformanceSamples,
    SignatureStatus,
    Supply,
    TransactionSignature,
    TransactionElement,
)


class AsyncClient:
    def __init__(
        self, endpoint: Text, local: bool = False, clean_response: bool = True
    ):
        """
        Async Solana RPC client.

        Args:
            endpoint (str): The RPC endpoint URL.
            local (bool): Skip endpoint validation. Defaults to False.
            clean_response (bool): Whether to unwrap RPC responses. Defaults to True.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL.")
        self.http = AsyncHTTPClient(endpoint)
        self.endpoint = endpoint
        self.clean_response = clean_response

    async def refresh_http(self) -> None:
        await self.http.refresh()

    # ========================================================================
    # Account Methods
    # ========================================================================

    async def get_account_info(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ):
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request("getAccountInfo", [str(public_key), config])
        if self.clean_response:
            if response["value"] is None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            return AccountInfo(response["value"])
        return response

    async def get_balance(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ):
        params: list = [str(public_key)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_multiple_accounts(
        self, pubkeys: List[str], commitment: Optional[Commitment] = None
    ):
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request("getMultipleAccounts", [pubkeys, config])
        if self.clean_response:
            return [AccountInfo(a) for a in response["value"] if a]
        return response

    async def get_program_accounts(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None,
        filters: Optional[List[Dict]] = None
    ):
        config: Dict[str, Any] = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        if filters:
            config["filters"] = filters
        response = await self.build_and_send_request("getProgramAccounts", [str(public_key), config])
        if self.clean_response:
            return [ProgramAccount(a) for a in response]
        return response

    async def get_largest_accounts(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getLargestAccounts", params if params else [None])
        if self.clean_response:
            return [LargestAccounts(a) for a in response["value"]]
        return response

    async def get_minimum_balance_for_rent_exemption(
        self, data_length: int, commitment: Optional[Commitment] = None
    ):
        params: list = [data_length]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getMinimumBalanceForRentExemption", params)

    # ========================================================================
    # Block Methods
    # ========================================================================

    async def get_block(self, slot: int, max_supported_transaction_version: int = 0):
        config = {"maxSupportedTransactionVersion": max_supported_transaction_version}
        response = await self.build_and_send_request("getBlock", [slot, config])
        if self.clean_response:
            return Block(response)
        return response

    async def get_block_height(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getBlockHeight", params if params else [None])

    async def get_block_production(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getBlockProduction", params if params else [None])
        if self.clean_response:
            return BlockProduction(response["value"])
        return response

    async def get_block_commitment(self, block: int):
        response = await self.build_and_send_request("getBlockCommitment", [block])
        if self.clean_response:
            return BlockCommitment(response)
        return response

    async def get_blocks(self, start_slot: int, end_slot: int | None = None):
        params: list = [start_slot]
        if end_slot:
            params.append(end_slot)
        return await self.build_and_send_request("getBlocks", params)

    async def get_blocks_with_limit(self, start_slot: int, limit: int):
        return await self.build_and_send_request("getBlocksWithLimit", [start_slot, limit])

    async def get_block_time(self, block: int):
        return await self.build_and_send_request("getBlockTime", [block])

    async def get_latest_blockhash(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getLatestBlockhash", params if params else [None])
        if self.clean_response:
            return BlockHash(response["value"])
        return response

    async def is_blockhash_valid(self, blockhash: Text, commitment: Optional[Commitment] = None):
        params: list = [blockhash]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("isBlockhashValid", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Cluster Methods
    # ========================================================================

    async def get_cluster_nodes(self):
        response = await self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(n) for n in response]
        return response

    async def get_epoch_info(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getEpochInfo", params if params else [None])
        if self.clean_response:
            return Epoch(response)
        return response

    async def get_epoch_schedule(self):
        response = await self.build_and_send_request("getEpochSchedule", [None])
        if self.clean_response:
            return EpochSchedule(response)
        return response

    async def get_first_available_block(self):
        return await self.build_and_send_request("getFirstAvailableBlock", [None])

    async def get_genesis_hash(self):
        return await self.build_and_send_request("getGenesisHash", [None])

    async def get_health(self):
        return await self.build_and_send_request("getHealth", [None])

    async def get_identity(self):
        response = await self.build_and_send_request("getIdentity", [None])
        if self.clean_response:
            return PubKeyIdentity(response)
        return response

    async def get_version(self):
        return await self.build_and_send_request("getVersion", [None])

    async def get_highest_snapshot_slot(self):
        return await self.build_and_send_request("getHighestSnapshotSlot", [None])

    async def get_leader_schedule(self, slot: Optional[int] = None):
        return await self.build_and_send_request("getLeaderSchedule", [slot])

    async def get_max_retransmit_slot(self):
        return await self.build_and_send_request("getMaxRetransmitSlot", [None])

    async def get_max_shred_insert_slot(self):
        return await self.build_and_send_request("getMaxShredInsertSlot", [None])

    async def get_slot(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getSlot", params if params else [None])

    async def get_slot_leader(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getSlotLeader", params if params else [None])

    async def get_slot_leaders(self, start_slot: int, limit: int):
        return await self.build_and_send_request("getSlotLeaders", [start_slot, limit])

    async def minimum_ledger_slot(self):
        return await self.build_and_send_request("minimumLedgerSlot", [None])

    async def get_vote_accounts(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getVoteAccounts", params if params else [None])

    # ========================================================================
    # Fee Methods
    # ========================================================================

    async def get_fee_for_message(self, message: Text, commitment: Optional[Commitment] = None):
        params: list = [message]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getFeeForMessage", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_recent_prioritization_fees(self, addresses: Optional[List[Text]] = None):
        params: list = []
        if addresses:
            params.append(addresses)
        return await self.build_and_send_request("getRecentPrioritizationFees", params if params else [None])

    # ========================================================================
    # Inflation Methods
    # ========================================================================

    async def get_inflation_governor(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getInflationGovernor", params if params else [None])
        if self.clean_response:
            return InflationGovernor(response)
        return response

    async def get_inflation_rate(self):
        response = await self.build_and_send_request("getInflationRate", [None])
        if self.clean_response:
            return InflationRate(response)
        return response

    async def get_inflation_reward(
        self, addresses: List[Text], commitment: Optional[Commitment] = None,
        epoch: Optional[int] = None
    ):
        params: list = [addresses]
        config: Dict[str, Any] = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if epoch is not None:
            config["epoch"] = epoch
        if config:
            params.append(config)
        response = await self.build_and_send_request("getInflationReward", params)
        if self.clean_response:
            return [InflationReward(r) for r in response if r]
        return response

    # ========================================================================
    # Supply / Stake
    # ========================================================================

    async def get_supply(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getSupply", params if params else [None])
        if self.clean_response:
            return Supply(response["value"])
        return response

    async def get_stake_minimum_delegation(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getStakeMinimumDelegation", params if params else [None])
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Token Methods
    # ========================================================================

    async def get_token_accounts_by_owner(
        self, public_key: Text | PublicKey, commitment: Optional[Commitment] = None, **kwargs
    ):
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError("You must pass either mint_id or program_id keyword argument")
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        encoding = kwargs.get("encoding", "jsonParsed")
        config: Dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request(
            "getTokenAccountsByOwner",
            [str(public_key), {"mint": mint_id} if mint_id else {"programId": program_id}, config],
        )
        if self.clean_response:
            return [ProgramAccount(a) for a in response["value"]]
        return response

    async def get_token_accounts_by_delegate(
        self, delegate: Text | PublicKey, commitment: Optional[Commitment] = None, **kwargs
    ):
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError("You must pass either mint_id or program_id keyword argument")
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        encoding = kwargs.get("encoding", "jsonParsed")
        config: Dict[str, Any] = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request(
            "getTokenAccountsByDelegate",
            [str(delegate), {"mint": mint_id} if mint_id else {"programId": program_id}, config],
        )
        if self.clean_response:
            return [ProgramAccount(a) for a in response["value"]]
        return response

    async def get_token_account_balance(
        self, token_account: Text | PublicKey, commitment: Optional[Commitment] = None
    ):
        params: list = [str(token_account)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getTokenAccountBalance", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_token_supply(self, mint: Text | PublicKey, commitment: Optional[Commitment] = None):
        params: list = [str(mint)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getTokenSupply", params)
        if self.clean_response:
            return response["value"]
        return response

    async def get_token_largest_accounts(self, mint: Text | PublicKey, commitment: Optional[Commitment] = None):
        params: list = [str(mint)]
        if commitment:
            params.append(validate_commitment(commitment))
        response = await self.build_and_send_request("getTokenLargestAccounts", params)
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Transaction Methods
    # ========================================================================

    async def get_transaction(
        self, signature: Text, max_supported_transaction_version: int = 0,
        commitment: Optional[Commitment] = None
    ):
        config: Dict[str, Any] = {"maxSupportedTransactionVersion": max_supported_transaction_version}
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request("getTransaction", [signature, config])
        if self.clean_response:
            if response is None:
                raise ValueError("Transaction not found")
            return TransactionElement(response)
        return response

    async def get_transaction_count(self, commitment: Optional[Commitment] = None):
        params: list = []
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("getTransactionCount", params if params else [None])

    async def get_signatures_for_address(
        self, acct_address: Text, limit: Optional[int] = None,
        before: Optional[Text] = None, until: Optional[Text] = None,
        commitment: Optional[Commitment] = None,
    ):
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
        response = await self.build_and_send_request("getSignaturesForAddress", params)
        if self.clean_response:
            return [TransactionSignature(s) for s in response]
        return response

    async def get_signature_statuses(
        self, transaction_sigs: List[Text], search_transaction_history: bool = False
    ):
        params: list = [transaction_sigs]
        if search_transaction_history:
            params.append({"searchTransactionHistory": True})
        response = await self.build_and_send_request("getSignatureStatuses", params)
        if self.clean_response:
            return [SignatureStatus(s) for s in response["value"] if s]
        return response

    async def get_recent_performance_samples(self, limit: Optional[int] = None):
        params: list = [limit] if limit else [None]
        response = await self.build_and_send_request("getRecentPerformanceSamples", params)
        if self.clean_response:
            return [RecentPerformanceSamples(s) for s in response]
        return response

    async def simulate_transaction(
        self, transaction: Text, sig_verify: bool = False,
        commitment: Optional[Commitment] = None,
        replace_recent_blockhash: bool = False,
    ):
        config: Dict[str, Any] = {
            "encoding": "base64",
            "sigVerify": sig_verify,
            "replaceRecentBlockhash": replace_recent_blockhash,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = await self.build_and_send_request("simulateTransaction", [transaction, config])
        if self.clean_response:
            return response["value"]
        return response

    # ========================================================================
    # Action Methods
    # ========================================================================

    async def request_airdrop(
        self, public_key: PublicKey | Text, lamports: int,
        commitment: Optional[Commitment] = None
    ):
        params: list = [str(public_key), lamports]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request("requestAirdrop", params)

    async def send_transaction(
        self, transaction: Transaction, options: Optional[Dict] = None
    ):
        recent_blockhash = transaction.recent_blockhash
        if recent_blockhash is None:
            blockhash_resp = await self.get_latest_blockhash()
            recent_blockhash = blockhash_resp.blockhash

        if options is None:
            options = {"encoding": "base64"}

        transaction.recent_blockhash = recent_blockhash
        transaction.sign()

        return await self.build_and_send_request(
            "sendTransaction", [transaction.serialize(), options]
        )

    # ========================================================================
    # Internal
    # ========================================================================

    async def build_and_send_request(
        self, method: str, params: List[Any]
    ):
        data: Dict[str, Any] = self.http.build_data(method=method, params=params)
        res = await self.http.send(data)
        if self.clean_response:
            if "error" in res:
                raise RPCRequestError(
                    f"RPC Error {res['error']['code']}: {res['error']['message']}"
                )
            result = res.get("result")
            if result is None or isinstance(result, (dict, list, str, int, float, bool)):
                return result
            else:
                raise RPCRequestError(f"Unexpected response type: {type(result).__name__}")
        return res
