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
        Initializes a new instance of the Client class.

        Args:
            endpoint (str): The endpoint to connect to.
            local (bool, optional): Whether to use a local development endpoint. Defaults to False.
            clean_response (bool, optional): Whether to clean the response from the RPC endpoint. Defaults to True.

        Raises:
            ValueError: If the endpoint is not valid and local is False.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL.")
        self.http = HTTPClient(endpoint)
        self.endpoint = endpoint
        self.clean_response = clean_response

    def refresh_http(self) -> None:
        """
        Refreshes the HTTP client.
        """
        self.http.refresh()

    def get_account_info(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[AccountInfoType] | AccountInfo:
        """
        Returns all the account info for the specified public key.

        Args:
            public_key (PublicKey | str): The public key of the account.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request(
            "getAccountInfo", [public_key, config]
        )
        if self.clean_response:
            if response["value"] == None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            return AccountInfo(response["value"])
        return response

    def get_balance(
        self, public_key: PublicKey | Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the balance of the specified public key.

        Args:
            public_key (PublicKey | Text): The public key of the account.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getBalance", [public_key, config])
        if self.clean_response:
            return response["value"]

        return response

    def get_block(
        self,
        slot: int,
        commitment: Optional[Commitment] = None,
        max_supported_transaction_version: Optional[int] = 0,
    ) -> RPCResponse[BlockType] | Block:
        """
        Returns the block at the specified slot.

        Args:
            slot (int): The slot of the block.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            max_supported_transaction_version (int, optional): The highest transaction version to return.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {
            "maxSupportedTransactionVersion": max_supported_transaction_version
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getBlock", [slot, config])
        if self.clean_response:
            return Block(response)
        return response

    def get_block_height(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the current block height.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request("getBlockHeight", [commitment])

    def get_block_production(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[BlockProductionType] | BlockProduction:
        """
        Returns the block production information.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getBlockProduction", [commitment])
        if self.clean_response:
            return BlockProduction(response["value"])
        return response

    def get_block_commitment(
        self, block: int
    ) -> RPCResponse[BlockCommitmentType] | BlockCommitment:
        """
        Returns the block commitment information for the specified block.

        Args:
            block (int): The block number.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getBlockCommitment", [block])
        if self.clean_response:
            return BlockCommitment(response)
        return response

    def get_blocks(
        self,
        start_slot: int,
        end_slot: int | None = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[List[int]] | List[int]:
        """
        Returns the blocks in the specified range.

        Args:
            start_slot (int): The start slot.
            end_slot (int | None, optional): The end slot. Defaults to None.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        params = [start_slot]
        if end_slot is not None:
            params.append(end_slot)
        if commitment:
            params.append(commitment)

        return self.build_and_send_request("getBlocks", params)

    def get_blocks_with_limit(
        self, start_slot: int, limit: int
    ) -> RPCResponse[List[int]] | List[int]:
        """
        Returns the blocks in the specified range with a limit.

        Args:
            start_slot (int): The start slot.
            limit (int): The limit.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getBlocksWithLimit", [start_slot, limit])

    def get_block_time(self, block: int) -> RPCResponse[int] | int:
        """
        Returns the block time for the specified block.

        Args:
            block (int): The block number.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getBlockTime", [block])

    def get_cluster_nodes(
        self,
    ) -> RPCResponse[List[ClusterNodeType]] | List[ClusterNode]:
        """
        Returns the cluster nodes.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(node) for node in response]
        return response

    def get_epoch_info(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[EpochType] | Epoch:
        """
        Returns the epoch information.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getEpochInfo", [commitment])
        if self.clean_response:
            return Epoch(response)
        return response

    def get_epoch_schedule(self) -> RPCResponse[EpochScheduleType] | EpochSchedule:
        """
        Returns the epoch schedule.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getEpochSchedule", [None])
        if self.clean_response:
            return EpochSchedule(response)
        return response

    def get_fee_for_message(
        self, message: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the fee for the specified message.

        Args:
            message (str): The message.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getFeeForMessage", [message, commitment]
        )
        if self.clean_response:
            return response["value"]
        return response

    def get_recent_prioritization_fees(
        self, addresses: Optional[List[PublicKey | Text]] = None
    ) -> RPCResponse[List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """
        Returns recent prioritization fees for the supplied writable accounts.

        Args:
            addresses (list, optional): Up to 128 account public keys.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [[str(address) for address in addresses]] if addresses else [None]
        return self.build_and_send_request("getRecentPrioritizationFees", params)


    def get_first_available_block(self) -> RPCResponse[int] | int:
        """
        Returns the first available block.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getFirstAvailableBlock", [None])

    def get_genesis_hash(self) -> RPCResponse[str] | str:
        """
        Returns the genesis hash.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getGenesisHash", [None])

    def get_health(self) -> RPCResponse[Literal["ok"]] | Literal["ok"]:
        """
        Returns the health.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getHealth", [None])

    def get_identity(self) -> RPCResponse[PubKeyIdentityType] | PubKeyIdentity:
        """
        Returns the identity.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getIdentity", [None])
        if self.clean_response:
            return PubKeyIdentity(response)
        return response

    def get_version(self) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """
        Returns the current Solana version running on the RPC node.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getVersion", [None])

    def get_highest_snapshot_slot(
        self,
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """
        Returns the highest full and incremental snapshot slots on the RPC node.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getHighestSnapshotSlot", [None])

    def get_inflation_governor(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[InflationGovernorType] | InflationGovernor:
        """
        Returns the inflation governor.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getInflationGovernor", [commitment])
        if self.clean_response:
            return InflationGovernor(response)
        return response

    def get_inflation_rate(self) -> RPCResponse[InflationRateType] | InflationRate:
        """
        Returns the inflation rate.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getInflationRate", [None])
        if self.clean_response:
            return InflationRate(response)
        return response

    def get_inflation_reward(
        self, addresses: List[Text], commitment: Optional[Commitment] = None
    ) -> RPCResponse[List[InflationRewardType]] | List[InflationReward]:
        """
        Returns the inflation reward for the specified addresses.

        Args:
            addresses (List[str]): The addresses.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [addresses]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("getInflationReward", params)
        if self.clean_response:
            return [InflationReward(reward) for reward in response]
        return response

    def get_largest_accounts(
        self,
    ) -> RPCResponse[List[LargestAccountsType]] | List[LargestAccounts]:
        """
        Returns the largest accounts.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getLargestAccounts", [None])
        if self.clean_response:
            return [LargestAccounts(account) for account in response["value"]]
        return response

    def get_leader_schedule(
        self,
        slot: Optional[int] = None,
        commitment: Optional[Commitment] = None,
    ) -> (
        RPCResponse[Dict[str, Union[List[int], Any]]] | Dict[str, Union[List[int], Any]]
    ):
        """
        Returns the leader schedule.

        Args:
            slot (int, optional): The slot used to identify an epoch.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [slot]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("getLeaderSchedule", params)

    def get_max_retransmit_slot(self) -> RPCResponse[int] | int:
        """
        Returns the maximum retransmit slot.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getMaxRetransmitSlot", [None])

    def get_max_shred_insert_slot(self) -> RPCResponse[int] | int:
        """
        Returns the maximum shred insert slot.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getMaxShredInsertSlot", [None])

    def get_minimum_balance_for_rent_exemption(
        self, acct_length: int, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the minimum balance for rent exemption.

        Args:
            acct_length (int): The length of the account.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request(
            "getMinimumBalanceForRentExemption", [acct_length, commitment]
        )

    def get_multiple_accounts(
        self,
        pubkeys: List[str],
        commitment: Optional[Commitment] = None,
        encoding: Text = "base64",
    ) -> RPCResponse[List[AccountInfoType]] | List[AccountInfo]:
        """
        Returns the multiple accounts.

        Args:
            pubkeys (list): The public keys.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            encoding (str, optional): The account data encoding.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request(
            "getMultipleAccounts", [pubkeys, config]
        )
        if self.clean_response:
            return [
                AccountInfo(account) if account is not None else None
                for account in response["value"]
            ]
        return response

    def get_program_accounts(
        self,
        public_key: PublicKey | Text,
        commitment: Optional[Commitment] = None,
        filters: Optional[List[Dict]] = None,
        encoding: Text = "base64",
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """
        Returns the program accounts.

        Args:
            public_key (PublicKey): The public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            filters (list, optional): Filters applied to program accounts.
            encoding (str, optional): The account data encoding.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if filters:
            config["filters"] = filters
        response = self.build_and_send_request(
            "getProgramAccounts", [public_key, config]
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response]
        return response

    def get_latest_blockhash(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[BlockHashType] | BlockHash:
        """
        Returns the recent blockhash.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getLatestBlockhash", [commitment])
        if self.clean_response:
            return BlockHash(response["value"])
        return response

    def is_blockhash_valid(
        self, blockhash: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse[bool] | bool:
        """
        Returns whether the specified blockhash is still valid.

        Args:
            blockhash (str): The blockhash to check.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [blockhash]
        if commitment:
            params.append(validate_commitment(commitment))
        response = self.build_and_send_request("isBlockhashValid", params)
        if self.clean_response:
            return response["value"]
        return response

    def get_recent_performance_samples(
        self, limit: Optional[int] = None
    ) -> (
        RPCResponse[List[RecentPerformanceSamplesType]] | List[RecentPerformanceSamples]
    ):
        """
        Returns the recent performance samples.

        Args:
            limit (int, optional): The maximum number of samples to return.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request(
            "getRecentPerformanceSamples", [limit]
        )
        if self.clean_response:
            return [RecentPerformanceSamples(sample) for sample in response]
        return response

    def get_signatures_for_address(
        self,
        acct_address: Text,
        limit: Optional[int] = None,
        before: Optional[Text] = None,
        until: Optional[Text] = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[List[TransactionSignatureType]] | List[TransactionSignature]:
        """
        Returns the signatures for the specified account address.

        Args:
            acct_address (str): The account address.
            limit (int, optional): The maximum number of signatures to return.
            before (str, optional): Starts searching before this signature.
            until (str, optional): Stops searching at this signature.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [acct_address]
        options = {}

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
            return [TransactionSignature(signature) for signature in response]
        return response

    def get_signature_statuses(
        self,
        transaction_sigs: List[Text],
        search_transaction_history: bool = False,
    ) -> RPCResponse[List[SignatureStatusType]] | List[SignatureStatus]:
        """
        Returns the signature statuses for the specified transaction signatures.

        Args:
            transaction_sigs (List[str]): The transaction signatures.
            search_transaction_history (bool, optional): Searches the node's transaction history.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [transaction_sigs]
        if search_transaction_history:
            params.append({"searchTransactionHistory": True})
        response = self.build_and_send_request("getSignatureStatuses", params)
        if self.clean_response:
            return [SignatureStatus(status) for status in response["value"]]
        return response

    def get_slot(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the current slot.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request("getSlot", [config])

    def get_slot_leader(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[str] | str:
        """
        Returns the identity public key of the current slot leader.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request("getSlotLeader", [config])

    def get_slot_leaders(
        self, start_slot: int, limit: int
    ) -> RPCResponse[List[str]] | List[str]:
        """
        Returns the leader public key for each slot in a range.

        Args:
            start_slot (int): The first slot in the range.
            limit (int): The number of slot leaders to return.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getSlotLeaders", [start_slot, limit])

    def minimum_ledger_slot(self) -> RPCResponse[int] | int:
        """
        Returns the lowest slot that the RPC node retains in its ledger.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("minimumLedgerSlot", [None])

    def get_vote_accounts(
        self,
        commitment: Optional[Commitment] = None,
        vote_public_key: PublicKey | Text | None = None,
        keep_unstaked_delinquents: Optional[bool] = None,
        delinquent_slot_distance: Optional[int] = None,
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """
        Returns current and delinquent vote accounts visible to the RPC node.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.
            vote_public_key (PublicKey | str, optional): Restricts results to one vote account.
            keep_unstaked_delinquents (bool, optional): Includes delinquent accounts with no active stake.
            delinquent_slot_distance (int, optional): Overrides the delinquent slot distance.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if vote_public_key is not None:
            config["votePubkey"] = str(vote_public_key)
        if keep_unstaked_delinquents is not None:
            config["keepUnstakedDelinquents"] = keep_unstaked_delinquents
        if delinquent_slot_distance is not None:
            config["delinquentSlotDistance"] = delinquent_slot_distance
        return self.build_and_send_request(
            "getVoteAccounts", [config] if config else [None]
        )

    def get_supply(
        self,
        commitment: Optional[Commitment] = None,
        exclude_non_circulating_accounts_list: bool = False,
    ) -> RPCResponse[SupplyType] | Supply:
        """
        Returns the supply.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.
            exclude_non_circulating_accounts_list (bool, optional): Omits the non-circulating account list.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = {
            "excludeNonCirculatingAccountsList": exclude_non_circulating_accounts_list
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request("getSupply", [config])
        if self.clean_response:
            return Supply(response["value"])
        return response

    def get_stake_minimum_delegation(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the minimum stake delegation in lamports.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getStakeMinimumDelegation", [config]
        )
        if self.clean_response:
            return response["value"]
        return response

    def get_token_accounts_by_owner(
        self,
        public_key: Text | PublicKey,
        commitment: Optional[Commitment] = None,
        **kwargs,
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """
        Returns the token accounts for the specified owner.

        Args:
            public_key (str | PublicKey): The public key of the owner.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If neither mint_id nor program_id is passed as a keyword argument.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError(
                "You must pass either mint_id or program_id keyword argument"
            )
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        # Who doesn't like JSON?
        encoding = kwargs.get("encoding", "jsonParsed")

        config = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if kwargs.get("min_context_slot") is not None:
            config["minContextSlot"] = kwargs["min_context_slot"]
        if kwargs.get("data_slice") is not None:
            config["dataSlice"] = kwargs["data_slice"]
        response = self.build_and_send_request(
            "getTokenAccountsByOwner",
            [
                str(public_key),
                {"mint": mint_id} if mint_id else {"programId": program_id},
                config,
            ],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_token_accounts_by_delegate(
        self,
        delegate: Text | PublicKey,
        commitment: Optional[Commitment] = None,
        **kwargs,
    ) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """
        Returns token accounts whose approved delegate matches an address.

        Args:
            delegate (str | PublicKey): The approved delegate public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            **kwargs: The mint_id or program_id filter and optional encoding.

        Raises:
            ValueError: If neither mint_id nor program_id is passed as a keyword argument.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        if "mint_id" not in kwargs and "program_id" not in kwargs:
            raise ValueError(
                "You must pass either mint_id or program_id keyword argument"
            )
        mint_id = kwargs.get("mint_id")
        program_id = kwargs.get("program_id")
        config = {"encoding": kwargs.get("encoding", "jsonParsed")}
        if commitment:
            config.update(validate_commitment(commitment))
        if kwargs.get("min_context_slot") is not None:
            config["minContextSlot"] = kwargs["min_context_slot"]
        if kwargs.get("data_slice") is not None:
            config["dataSlice"] = kwargs["data_slice"]

        response = self.build_and_send_request(
            "getTokenAccountsByDelegate",
            [
                str(delegate),
                {"mint": mint_id} if mint_id else {"programId": program_id},
                config,
            ],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response["value"]]
        return response

    def get_token_account_balance(
        self,
        token_account: Text | PublicKey,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the token account balance for the specified owner.

        Args:
            token_account (str | PublicKey): The token account pubkey.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """

        config = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getTokenAccountBalance",
            [
                str(token_account),
                config,
            ],
        )
        if self.clean_response:
            return response["value"]
        return response

    def get_token_supply(
        self,
        mint: Text | PublicKey,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """
        Returns the total supply of an SPL Token mint.

        Args:
            mint (str | PublicKey): The token mint public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getTokenSupply", [str(mint), config]
        )
        if self.clean_response:
            return response["value"]
        return response

    def get_token_largest_accounts(
        self,
        mint: Text | PublicKey,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """
        Returns the 20 largest accounts for an SPL Token mint.

        Args:
            mint (str | PublicKey): The token mint public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getTokenLargestAccounts", [str(mint), config]
        )
        if self.clean_response:
            return response["value"]
        return response

    def get_transaction(
        self,
        signature: Text,
        commitment: Optional[Commitment] = None,
        max_supported_transaction_version: Optional[int] = 0,
        encoding: Text = "json",
    ) -> RPCResponse[TransactionElementType] | TransactionElement:
        """
        Sends a request to the Solana RPC endpoint to retrieve a transaction by its signature.

        Args:
            signature (str): The signature of the transaction to retrieve.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            max_supported_transaction_version (int, optional): Set the max transaction version to return in responses
            encoding (str, optional): The transaction encoding.

        Returns:
            RPCResponse: The response from the Solana RPC endpoint.
        """
        config = {
            "encoding": encoding,
            "maxSupportedTransactionVersion": max_supported_transaction_version,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        response = self.build_and_send_request(
            "getTransaction", [signature, config]
        )
        if self.clean_response:
            if response == None:
                raise ValueError("Transaction not found")
            return TransactionElement(response)
        return response

    def get_transaction_count(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse[int] | int:
        """
        Returns the total number of transactions processed by the ledger.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request("getTransactionCount", [config])

    def simulate_transaction(
        self,
        transaction: Text,
        sig_verify: bool = False,
        commitment: Optional[Commitment] = None,
        replace_recent_blockhash: bool = False,
        min_context_slot: Optional[int] = None,
        inner_instructions: bool = False,
        accounts: Optional[Dict] = None,
    ) -> RPCResponse[Dict[str, Any]] | Dict[str, Any]:
        """
        Simulates a base64-encoded transaction without broadcasting it.

        Args:
            transaction (str): The base64-encoded transaction.
            sig_verify (bool, optional): Whether to verify transaction signatures.
            commitment (Commitment, optional): The level of commitment desired when querying state.
            replace_recent_blockhash (bool, optional): Whether the node should replace the blockhash.
            min_context_slot (int, optional): The minimum slot allowed for evaluation.
            inner_instructions (bool, optional): Whether to include inner instructions.
            accounts (dict, optional): Account data to return after simulation.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        if sig_verify and replace_recent_blockhash:
            raise ValueError(
                "sig_verify and replace_recent_blockhash cannot both be enabled"
            )
        config = {
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
        response = self.build_and_send_request(
            "simulateTransaction", [transaction, config]
        )
        if self.clean_response:
            return response["value"]
        return response

    def build_and_send_request(
        self, method, params: List[Any]
    ) -> RPCResponse | Dict[str, Any] | List[Dict[str, Any]]:
        """
        Builds and sends an RPC request to the server.

        Args:
            method (str): The RPC method to call.
            params (List[Any]): The parameters to pass to the RPC method.

        Returns:
            RPCResponse: The response from the server.
        """
        data: Dict[str, Any] = self.http.build_data(method=method, params=params)
        res: RPCResponse = self.http.send(data)
        if self.clean_response:
            if "error" in res:
                raise RPCRequestError(
                    f"Failed to fetch data from RPC endpoint. Error {res['error']['code']}: {res['error']['message']}"
                )

            if (
                isinstance(res["result"], dict)
                or isinstance(res["result"], list)
                or isinstance(res["result"], str)
                or isinstance(res["result"], int)
                or res["result"] == None
            ):
                return res["result"]
            else:
                raise RPCRequestError(
                    f"Invalid response from RPC endpoint. Expected types dict | list | str, got {type(res['result']).__name__}"
                )

        return res

    # Non "get" methods
    def request_airdrop(
        self,
        public_key: PublicKey | Text,
        lamports: int,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse[str] | str:
        """
        Requests an airdrop of lamports to the specified public key.

        Args:
            public_key (PublicKey | Text): The public key of the account to receive the airdrop.
            lamports (int): The amount of lamports to request in the airdrop.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the Solana JSON RPC API.
        """
        params = [public_key, lamports]
        if commitment:
            params.append(validate_commitment(commitment))
        return self.build_and_send_request("requestAirdrop", params)

    def send_transaction(self, transaction: Transaction, options: Optional[Dict] = None) -> RPCResponse[str] | str:
        """
        Sends a transaction to the Solana network.

        Args:
            transaction (Transaction): The transaction to send.
            options (Dict): Options for sending transactions

        Returns:
            RPCResponse: The response from the Solana network.
        """
        recent_blockhash = transaction.recent_blockhash

        if recent_blockhash is None:
            blockhash_resp = self.get_latest_blockhash()
            recent_blockhash = blockhash_resp.blockhash
        
        if options:
            options = options
        else:
            options = {"encoding": "base64"}

        transaction.recent_blockhash = recent_blockhash
        transaction.sign()

        return self.build_and_send_request(
            "sendTransaction", [transaction.serialize(), options]
        )
