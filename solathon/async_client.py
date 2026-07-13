from __future__ import annotations

from typing import Any, Dict, List, Optional, Text, Union

from .core.http import AsyncHTTPClient
from .core.types import Commitment, RPCResponse
from .publickey import PublicKey
from .transaction import Transaction
from .utils import validate_commitment


class AsyncClient:
    def __init__(self, endpoint: Text, local: bool = False):
        """
        Initializes an AsyncClient object.

        Args:
        - endpoint (str): The endpoint URL for the Solana RPC server.
        - local (bool): Whether to use a local development endpoint or not. Defaults to False.

        Raises:
        - ValueError: If the endpoint is not valid and not a local development endpoint.
        """
        if not local and not endpoint.startswith(("http://", "https://")):
            raise ValueError("Invalid RPC endpoint. Must be a valid HTTP/HTTPS URL.")
        self.http = AsyncHTTPClient(endpoint)
        self.endpoint = endpoint

    async def refresh_http(self) -> None:
        """
        Refreshes the HTTP client.
        """
        await self.http.refresh()

    async def get_account_info(
        self,
        public_key: PublicKey | Text,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the account information for a given public key.

        Args:
        - public_key (PublicKey | str): The public key of the account.
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = {"encoding": "base64"}
        if commitment:
            config.update(validate_commitment(commitment))
        return await self.build_and_send_request_async(
            "getAccountInfo", [public_key, config]
        )

    async def get_balance(
        self,
        public_key: PublicKey | Text,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the balance of a given account.

        Args:
        - public_key (PublicKey | str): The public key of the account.
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getBalance", [public_key, config]
        )

    async def get_block(
        self,
        slot: int,
        commitment: Optional[Commitment] = None,
        max_supported_transaction_version: Optional[int] = 0,
    ) -> RPCResponse:
        """
        Returns the block information for a given slot.

        Args:
        - slot (int): The slot of the block.
        - commitment (Commitment, optional): The level of commitment desired when querying state.
        - max_supported_transaction_version (int, optional): The highest transaction version to return.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = {
            "maxSupportedTransactionVersion": max_supported_transaction_version
        }
        if commitment:
            config.update(validate_commitment(commitment))
        return await self.build_and_send_request_async("getBlock", [slot, config])

    async def get_block_height(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the current block height.

        Args:
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getBlockHeight", [config])

    async def get_block_production(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the block production information.

        Args:
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getBlockProduction", [config]
        )

    async def get_block_commitment(self, block: int) -> RPCResponse:
        """
        Returns the block commitment information for a given block.

        Args:
        - block (int): The block number.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getBlockCommitment", [block])

    async def get_blocks(
        self,
        start_slot: int,
        end_slot: int | None = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the block information for a range of slots.

        Args:
        - start_slot (int): The starting slot.
        - end_slot (int | None): The ending slot. Defaults to None.
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        params = [start_slot]
        if end_slot is not None:
            params.append(end_slot)
        if commitment:
            params.append(validate_commitment(commitment))

        return await self.build_and_send_request_async("getBlocks", params)

    async def get_blocks_with_limit(self, start_slot: int, limit: int) -> RPCResponse:
        """
        Returns the block information for a range of slots with a limit.

        Args:
        - start_slot (int): The starting slot.
        - limit (int): The maximum number of blocks to return.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async(
            "getBlocksWithLimit", [start_slot, limit]
        )

    async def get_block_time(self, block: int) -> RPCResponse:
        """
        Returns the block time for a given block.

        Args:
        - block (int): The block number.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getBlockTime", [block])

    async def get_cluster_nodes(self) -> RPCResponse:
        """
        Returns the cluster nodes information.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getClusterNodes", [None])

    async def get_epoch_info(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the epoch information.

        Args:
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getEpochInfo", [config])

    async def get_epoch_schedule(self) -> RPCResponse:
        """
        Returns the epoch schedule information.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getEpochSchedule", [None])

    async def get_fee_for_message(
        self, message: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the fee for a given message.

        Args:
        - message (str): The message.
        - commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        params = [message]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request_async("getFeeForMessage", params)

    async def get_recent_prioritization_fees(
        self, addresses: Optional[List[PublicKey | Text]] = None
    ) -> RPCResponse:
        """
        Returns recent prioritization fees for the supplied writable accounts.

        Args:
            addresses (list, optional): Up to 128 account public keys.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [[str(address) for address in addresses]] if addresses else [None]
        return await self.build_and_send_request_async(
            "getRecentPrioritizationFees", params
        )

    async def get_first_available_block(self) -> RPCResponse:
        """
        Returns the first available block.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getFirstAvailableBlock", [None])

    async def get_genesis_hash(self) -> RPCResponse:
        """
        Returns the genesis hash.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getGenesisHash", [None])

    async def get_health(self) -> RPCResponse:
        """
        Returns the health information.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getHealth", [None])

    async def get_identity(self) -> RPCResponse:
        """
        Returns the identity information.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getIdentity", [None])

    async def get_version(self) -> RPCResponse:
        """
        Returns the current Solana version running on the RPC node.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return await self.build_and_send_request_async("getVersion", [None])

    async def get_highest_snapshot_slot(self) -> RPCResponse:
        """
        Returns the highest full and incremental snapshot slots on the RPC node.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return await self.build_and_send_request_async(
            "getHighestSnapshotSlot", [None]
        )

    async def get_inflation_governor(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the inflation governor information.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getInflationGovernor", [config])

    async def get_inflation_rate(self) -> RPCResponse:
        """
        Returns the inflation rate.

        Returns:
        - RPCResponse: The response from the Solana RPC server.
        """
        return await self.build_and_send_request_async("getInflationRate", [None])

    async def get_inflation_reward(
        self,
        addresses: List[Text],
        commitment: Optional[Commitment] = None,
        epoch: Optional[int] = None,
    ) -> RPCResponse:
        """
        Get the inflation reward for a list of addresses.

        Args:
            addresses (List[Text]): A list of addresses to get the inflation reward for.

        Returns:
            RPCResponse: The response from the RPC server.
        """
        config = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if epoch is not None:
            config["epoch"] = epoch
        params = [addresses]
        if config:
            params.append(config)
        return await self.build_and_send_request_async("getInflationReward", params)

    async def get_largest_accounts(
        self,
        commitment: Optional[Commitment] = None,
        filter: Optional[Text] = None,
    ) -> RPCResponse:
        """
        Returns the largest accounts on the Solana blockchain.

        :return: An RPCResponse object containing the response from the Solana node.
        """
        config = {}
        if commitment:
            config.update(validate_commitment(commitment))
        if filter:
            config["filter"] = filter
        return await self.build_and_send_request_async(
            "getLargestAccounts", [config] if config else [None]
        )

    async def get_leader_schedule(
        self,
        slot: Optional[int] = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Sends a request to the Solana RPC endpoint to retrieve the leader schedule.

        Args:
            slot (int, optional): The slot used to identify an epoch.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        params = [slot]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request_async("getLeaderSchedule", params)

    async def get_max_retransmit_slot(self) -> RPCResponse:
        """
        Sends a request to get the maximum retransmit slot from the server.

        Returns:
            An RPCResponse object containing the server's response.
        """
        return await self.build_and_send_request_async("getMaxRetransmitSlot", [None])

    async def get_max_shred_insert_slot(self) -> RPCResponse:
        """
        Sends a request to get the maximum shred insert slot from the Solana RPC endpoint.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return await self.build_and_send_request_async("getMaxShredInsertSlot", [None])

    async def get_minimum_balance_for_rent_exemption(
        self,
        acct_length: int,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the minimum balance needed to create an account with the given data size.

        :param acct_length: The length of the account data.
        :type acct_length: int
        :return: The minimum balance needed to create an account with the given data size.
        :rtype: RPCResponse
        """
        config = validate_commitment(commitment) if commitment else None
        params = [acct_length]
        if config:
            params.append(config)
        return await self.build_and_send_request_async(
            "getMinimumBalanceForRentExemption", params
        )

    async def get_multiple_accounts(
        self,
        pubkeys: List,
        commitment: Optional[Commitment] = None,
        encoding: Text = "base64",
    ) -> RPCResponse:
        """
        Sends a request to the Solana RPC endpoint to retrieve multiple accounts
        associated with the given public keys.

        Args:
            pubkeys (list): A list of public keys associated with the accounts to retrieve.

        Returns:
            RPCResponse: The response from the Solana RPC endpoint.
        """
        config = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        return await self.build_and_send_request_async(
            "getMultipleAccounts", [pubkeys, config]
        )

    async def get_program_accounts(
        self,
        public_key: PublicKey | Text,
        commitment: Optional[Commitment] = None,
        filters: Optional[List[Dict]] = None,
        encoding: Text = "base64",
    ) -> RPCResponse:
        """
        Returns accounts associated with a given program.

        Args:
            public_key (PublicKey): The public key of the program.

        Returns:
            RPCResponse: The response from the RPC server.
        """
        config = {"encoding": encoding}
        if commitment:
            config.update(validate_commitment(commitment))
        if filters is not None:
            config["filters"] = filters
        return await self.build_and_send_request_async(
            "getProgramAccounts", [public_key, config]
        )

    async def get_latest_blockhash(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns a recent blockhash from the ledger.

        :return: RPCResponse object containing the recent blockhash.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getLatestBlockhash", [config])

    async def is_blockhash_valid(
        self, blockhash: Text, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
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
        return await self.build_and_send_request_async("isBlockhashValid", params)

    async def get_recent_performance_samples(
        self, limit: Optional[int] = None
    ) -> RPCResponse:
        """
        Sends a request to the server to get recent performance samples.

        Returns:
            RPCResponse: The response from the server.
        """
        return await self.build_and_send_request_async(
            "getRecentPerformanceSamples", [limit]
        )

    async def get_signatures_for_address(
        self,
        acct_address: Text,
        before: Optional[Text] = None,
        until: Optional[Text] = None,
        limit: Optional[int] = None,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns signatures for a given account address.

        :param acct_address: The account address to get signatures for.
        :type acct_address: str
        :return: The RPC response containing the signatures for the account address.
        :rtype: RPCResponse
        """
        config = {}
        if before:
            config["before"] = before
        if until:
            config["until"] = until
        if limit is not None:
            config["limit"] = limit
        if commitment:
            config.update(validate_commitment(commitment))
        params = [acct_address]
        if config:
            params.append(config)
        return await self.build_and_send_request_async(
            "getSignaturesForAddress", params
        )

    async def get_signature_statuses(
        self,
        transaction_sigs: List[Text],
        search_transaction_history: bool = False,
    ) -> RPCResponse:
        """
        Returns the current status of a list of signatures.

        Args:
            transaction_sigs (List[str]): List of transaction signatures to check status for.

        Returns:
            RPCResponse: Response object containing the status of the signatures.
        """
        return await self.build_and_send_request_async(
            "getSignatureStatuses",
            [transaction_sigs, {"searchTransactionHistory": search_transaction_history}],
        )

    async def get_slot(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Sends a request to the Solana RPC endpoint to retrieve the current slot.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getSlot", [config])

    async def get_slot_leader(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the identity public key of the current slot leader.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async("getSlotLeader", [config])

    async def get_slot_leaders(self, start_slot: int, limit: int) -> RPCResponse:
        """
        Returns the leader public key for each slot in a range.

        Args:
            start_slot (int): The first slot in the range.
            limit (int): The number of slot leaders to return.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return await self.build_and_send_request_async(
            "getSlotLeaders", [start_slot, limit]
        )

    async def minimum_ledger_slot(self) -> RPCResponse:
        """
        Returns the lowest slot that the RPC node retains in its ledger.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return await self.build_and_send_request_async("minimumLedgerSlot", [None])

    async def get_vote_accounts(
        self,
        commitment: Optional[Commitment] = None,
        vote_public_key: PublicKey | Text | None = None,
        keep_unstaked_delinquents: Optional[bool] = None,
        delinquent_slot_distance: Optional[int] = None,
    ) -> RPCResponse:
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
        return await self.build_and_send_request_async(
            "getVoteAccounts", [config] if config else [None]
        )

    async def get_supply(
        self,
        commitment: Optional[Commitment] = None,
        exclude_non_circulating_accounts_list: bool = False,
    ) -> RPCResponse:
        """
        Sends a request to the Solana blockchain to retrieve the current supply.

        Returns:
            RPCResponse: The response from the Solana blockchain.
        """
        config = {
            "excludeNonCirculatingAccountsList": exclude_non_circulating_accounts_list
        }
        if commitment:
            config.update(validate_commitment(commitment))
        return await self.build_and_send_request_async("getSupply", [config])

    async def get_stake_minimum_delegation(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the minimum stake delegation in lamports.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getStakeMinimumDelegation", [config]
        )

    async def get_token_accounts_by_owner(
        self, public_key: Union[Text, PublicKey], **kwargs
    ) -> RPCResponse:
        """
        Returns token accounts owned by a particular address.

        Args:
            public_key (Union[Text, PublicKey]): The public key of the address to query.
            **kwargs: Additional keyword arguments.
                mint_id (Optional[Text]): The mint ID of the token to query.
                program_id (Optional[Text]): The program ID of the token to query.
                encoding (Optional[Text]): The encoding format of the response. Defaults to "jsonParsed".

        Returns:
            RPCResponse: The response from the RPC server.
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
        return await self.build_and_send_request_async(
            "getTokenAccountsByOwner",
            [
                str(public_key),
                {"mint": mint_id} if mint_id else {"programId": program_id},
                config,
            ],
        )

    async def get_token_accounts_by_delegate(
        self,
        delegate: Text | PublicKey,
        commitment: Optional[Commitment] = None,
        **kwargs,
    ) -> RPCResponse:
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

        return await self.build_and_send_request_async(
            "getTokenAccountsByDelegate",
            [
                str(delegate),
                {"mint": mint_id} if mint_id else {"programId": program_id},
                config,
            ],
        )

    async def get_token_account_balance(
        self, token_account: Text | PublicKey, commitment: Optional[Commitment]=None,
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
        return await self.build_and_send_request_async(
            "getTokenAccountBalance",
            [
                str(token_account),
                config,
            ],
        )

    async def get_token_supply(
        self,
        mint: Text | PublicKey,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the total supply of an SPL Token mint.

        Args:
            mint (str | PublicKey): The token mint public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getTokenSupply", [str(mint), config]
        )

    async def get_token_largest_accounts(
        self,
        mint: Text | PublicKey,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Returns the 20 largest accounts for an SPL Token mint.

        Args:
            mint (str | PublicKey): The token mint public key.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getTokenLargestAccounts", [str(mint), config]
        )


    async def get_transaction(
        self,
        signature: Text,
        commitment: Optional[Commitment] = None,
        max_supported_transaction_version: Optional[int] = 0,
        encoding: Text = "json",
    ) -> RPCResponse:
        """
        Sends a request to the Solana RPC endpoint to retrieve a transaction by its signature.

        Args:
            signature (Text): The signature of the transaction to retrieve.

        Returns:
            RPCResponse: The response from the Solana RPC endpoint.
        """
        config = {
            "encoding": encoding,
            "maxSupportedTransactionVersion": max_supported_transaction_version,
        }
        if commitment:
            config.update(validate_commitment(commitment))
        return await self.build_and_send_request_async(
            "getTransaction", [signature, config]
        )

    async def get_transaction_count(
        self, commitment: Optional[Commitment] = None
    ) -> RPCResponse:
        """
        Returns the total number of transactions processed by the ledger.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        config = validate_commitment(commitment) if commitment else None
        return await self.build_and_send_request_async(
            "getTransactionCount", [config]
        )

    async def simulate_transaction(
        self,
        transaction: Text,
        sig_verify: bool = False,
        commitment: Optional[Commitment] = None,
        replace_recent_blockhash: bool = False,
        min_context_slot: Optional[int] = None,
        inner_instructions: bool = False,
        accounts: Optional[Dict] = None,
    ) -> RPCResponse:
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
        return await self.build_and_send_request_async(
            "simulateTransaction", [transaction, config]
        )

    # Non "get" methods
    async def request_airdrop(
        self,
        public_key: Union[PublicKey, Text],
        lamports: int,
        commitment: Optional[Commitment] = None,
    ) -> RPCResponse:
        """
        Requests an airdrop of the specified number of lamports to the specified public key.

        Args:
            public_key (PublicKey | Text): The public key to receive the airdrop.
            lamports (int): The number of lamports to request in the airdrop.

        Returns:
            RPCResponse: The response from the Solana JSON RPC API.
        """
        params = [public_key, lamports]
        if commitment:
            params.append(validate_commitment(commitment))
        return await self.build_and_send_request_async("requestAirdrop", params)

    async def send_transaction(self, transaction: Transaction) -> RPCResponse:
        """
        Sends a transaction to the Solana network.

        Args:
            transaction (Transaction): The transaction to send.

        Returns:
            RPCResponse: The response from the Solana network.
        """
        if not transaction.recent_blockhash:
            transaction.recent_blockhash = (await self.get_latest_blockhash())[
                "result"
            ]["value"]["blockhash"]

        transaction.sign()

        return await self.build_and_send_request_async(
            "sendTransaction", [transaction.serialize(), {"encoding": "base64"}]
        )

    async def build_and_send_request_async(
        self, method: Text, params: List[Any]
    ) -> RPCResponse:
        """
        Builds and sends an RPC request to the server.

        Args:
            method (Text): The RPC method to call.
            params (List[Any]): The parameters to pass to the RPC method.

        Returns:
            RPCResponse: The response from the server.
        """
        data: Dict[Text, Any] = self.http.build_data(method=method, params=params)
        res: RPCResponse = await self.http.send(data)
        return res
