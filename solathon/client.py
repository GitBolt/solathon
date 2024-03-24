from __future__ import annotations

from typing import Any, List, Literal, Optional, Text, Union

from .utils import RPCRequestError, validate_commitment
from .publickey import PublicKey
from .core.http import HTTPClient
from .transaction import Transaction
from .core.types import (BlockHash, BlockHashType, Commitment, LargestAccounts, LargestAccountsType, PubKeyIdentity, PubKeyIdentityType, RPCResponse, 
                         AccountInfo, AccountInfoType, Block, BlockType, BlockProductionType, BlockProduction, BlockCommitmentType, BlockCommitment, 
                         ClusterNode, ClusterNodeType, Epoch, EpochType, EpochSchedule, EpochScheduleType, InflationGovernor, InflationGovernorType, 
                         InflationRate, InflationRateType, InflationReward, InflationRewardType, ProgramAccount, ProgramAccountType, RecentPerformanceSamples, 
                         RecentPerformanceSamplesType, SignatureStatus, SignatureStatusType, Supply, SupplyType, TransactionSignature, TransactionSignatureType, 
                         TransactionElement, TransactionElementType)


ENDPOINTS = (
    "https://api.mainnet-beta.solana.com",
    "https://api.devnet.solana.com",
    "https://api.testnet.solana.com",
)

class Client:
    def __init__(self, endpoint: Text, local: bool = False, clean_response: bool=True):
        """
        Initializes a new instance of the Client class.

        Args:
            endpoint (str): The endpoint to connect to.
            local (bool, optional): Whether to use a local development endpoint. Defaults to False.
            clean_response (bool, optional): Whether to clean the response from the RPC endpoint. Defaults to True.

        Raises:
            ValueError: If the endpoint is not valid and local is False.
        """
        if not local and endpoint not in ENDPOINTS:
            raise ValueError(
                "Invalid cluster RPC endpoint provided"
                " (Refer to https://docs.solana.com/cluster/rpc-endpoints)."
                " Use the argument local to use a local development endpoint."
            )
        self.http = HTTPClient(endpoint)
        self.endpoint = endpoint
        self.clean_response = clean_response

    def refresh_http(self) -> None:
        """
        Refreshes the HTTP client.
        """
        self.http.refresh()

    def get_account_info(self, public_key: PublicKey | Text, commitment: Optional[Commitment]=None) -> RPCResponse[AccountInfoType] | AccountInfo:
        """
        Returns all the account info for the specified public key.

        Args:
            public_key (PublicKey | str): The public key of the account.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getAccountInfo", [public_key, commitment])
        if self.clean_response:
            if response['value'] == None:
                raise RPCRequestError(f"Account details not found: {public_key}")
            return AccountInfo(response['value'])
        return response

    def get_balance(self, public_key: PublicKey | Text, commitment: Optional[Commitment]=None) -> RPCResponse[int] | int:
        """
        Returns the balance of the specified public key.

        Args:
            public_key (PublicKey | Text): The public key of the account.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getBalance", [public_key, commitment])
        if self.clean_response:
            return response['value']

        return response

    def get_block(self, slot: int) -> RPCResponse[BlockType] | Block:
        """
        Returns the block at the specified slot.

        Args:
            slot (int): The slot of the block.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getBlock", [slot])
        if self.clean_response:
            return Block(response)
        return response

    def get_block_height(self, commitment: Optional[Commitment]=None) -> RPCResponse[int] | int:
        """
        Returns the current block height.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        return self.build_and_send_request("getBlockHeight", [commitment])

    def get_block_production(self, commitment: Optional[Commitment]=None) -> RPCResponse[BlockProductionType] | BlockProduction:
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
            return BlockProduction(response['value'])
        return response

    def get_block_commitment(self, block: int) -> RPCResponse[BlockCommitmentType] | BlockCommitment:
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

    def get_blocks(self, start_slot: int, end_slot: int | None = None, commitment: Optional[Commitment]=None) -> RPCResponse[List[int]] | List[int]:
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
        if end_slot:
            params.append(end_slot)
        params.append(commitment)

        return self.build_and_send_request("getBlocks", params)

    def get_blocks_with_limit(self, start_slot: int, limit: int) -> RPCResponse[List[int]] | List[int]:
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

    def get_cluster_nodes(self) -> RPCResponse[List[ClusterNodeType]] | List[ClusterNode]:
        """
        Returns the cluster nodes.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getClusterNodes", [None])
        if self.clean_response:
            return [ClusterNode(node) for node in response]
        return response

    def get_epoch_info(self, commitment: Optional[Commitment]=None) -> RPCResponse[EpochType] | Epoch:
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

    def get_fee_for_message(self, message: Text, commitment: Optional[Commitment]=None) -> RPCResponse[int] | int:
        """
        Returns the fee for the specified message.

        Args:
            message (str): The message.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getFeeForMessage", [message, commitment])
        if self.clean_response:
            return response['value']
        return response

    # Going to be deprecated
    def get_fees(self) -> RPCResponse:
        """
        Returns the fees.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getFees", [None])

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

    def get_inflation_governor(self, commitment: Optional[Commitment]=None) -> RPCResponse[InflationGovernorType] | InflationGovernor:
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

    def get_inflation_reward(self, addresses: List[Text], commitment: Optional[Commitment]=None) -> RPCResponse[List[InflationRewardType]] | List[InflationReward]:
        """
        Returns the inflation reward for the specified addresses.

        Args:
            addresses (list[str]): The addresses.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        addresses.append(commitment)
        response = self.build_and_send_request("getInflationReward", addresses)
        if self.clean_response:
            return [InflationReward(reward) for reward in response]
        return response

    def get_largest_accounts(self) -> RPCResponse[List[LargestAccountsType]] | List[LargestAccounts]:
        """
        Returns the largest accounts.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getLargestAccounts", [None])
        if self.clean_response:
            return [LargestAccounts(account) for account in response['value']]
        return response

    def get_leader_schedule(self) -> RPCResponse[dict[str, Union[List[int], Any]]] | dict[str, Union[List[int],Any]]:
        """
        Returns the leader schedule.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getLeaderSchedule", [None])

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

    def get_minimum_balance_for_rent_exemption(self, acct_length: int, commitment: Optional[Commitment]=None) -> RPCResponse[int] | int:
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

    def get_multiple_accounts(self, pubkeys: List[str]) -> RPCResponse[List[AccountInfoType]] | List[AccountInfo]:
        """
        Returns the multiple accounts.

        Args:
            pubkeys (list): The public keys.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getMultipleAccounts", pubkeys)
        if self.clean_response:
            return [AccountInfo(account) for account in response['value']]
        return response

    def get_program_accounts(self, public_key: PublicKey) -> RPCResponse[List[ProgramAccountType]] | List[ProgramAccount]:
        """
        Returns the program accounts.

        Args:
            public_key (PublicKey): The public key.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getProgramAccounts", [public_key])
        if self.clean_response:
            return [ProgramAccount(account) for account in response]
        return response

    # Will switch to getFeeForMessage (latest)
    def get_recent_blockhash(self, commitment: Optional[Commitment]=None) -> RPCResponse[BlockHashType] | BlockHash:
        """
        Returns the recent blockhash.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getRecentBlockhash", [commitment])
        if self.clean_response:
            return BlockHash(response['value'])
        return response

    def get_recent_performance_samples(self, commitment: Optional[Commitment]=None) -> RPCResponse[List[RecentPerformanceSamplesType]] | List[RecentPerformanceSamples]:
        """
        Returns the recent performance samples.

        Args:
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request("getRecentPerformanceSamples", [commitment])
        if self.clean_response:
            return [RecentPerformanceSamples(sample) for sample in response]
        return response

    def get_signatures_for_address(self, acct_address: Text) -> RPCResponse[List[TransactionSignatureType]] | List[TransactionSignature]:
        """
        Returns the signatures for the specified account address.

        Args:
            acct_address (str): The account address.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getSignaturesForAddress", [acct_address])
        if self.clean_response:
            return [TransactionSignature(signature) for signature in response]
        return response

    def get_signature_statuses(self, transaction_sigs: List[Text]) -> RPCResponse[List[SignatureStatusType]] | List[SignatureStatus]:
        """
        Returns the signature statuses for the specified transaction signatures.

        Args:
            transaction_sigs (list[str]): The transaction signatures.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getSignatureStatuses", transaction_sigs)
        if self.clean_response:
            return [SignatureStatus(status) for status in response['value']]
        return response

    def get_slot(self) -> RPCResponse[int] | int:
        """
        Returns the current slot.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        return self.build_and_send_request("getSlot", [None])

    def get_supply(self) -> RPCResponse[SupplyType] | Supply:
        """
        Returns the supply.

        Returns:
            RPCResponse: The response from the RPC endpoint.
        """
        response = self.build_and_send_request("getSupply", [None])
        if self.clean_response:
            return Supply(response['value'])
        return response

    def get_token_accounts_by_owner(
        self, public_key: Text | PublicKey, commitment: Optional[Commitment]=None, **kwargs
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

        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getTokenAccountsByOwner",
            [
                str(public_key),
                {"mint": mint_id} if mint_id else {"programId": program_id},
                {
                    "encoding": encoding,
                    "commitment": commitment
                },
            ],
        )
        if self.clean_response:
            return [ProgramAccount(account) for account in response['value']]
        return response

    def get_token_account_balance(
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

        commitment = validate_commitment(commitment) if commitment else None
        response = self.build_and_send_request(
            "getTokenAccountBalance",
            [
                str(token_account),
            ],
        )
        if self.clean_response:
            return response['value']
        return response


    def get_transaction(self, signature: Text, commitment: Optional[Commitment]=None) -> RPCResponse[TransactionElementType] | TransactionElement:
        """
        Sends a request to the Solana RPC endpoint to retrieve a transaction by its signature.

        Args:
            signature (str): The signature of the transaction to retrieve.
            commitment (Commitment, optional): The level of commitment desired when querying state.

        Returns:
            RPCResponse: The response from the Solana RPC endpoint.
        """
        response = self.build_and_send_request("getTransaction", [signature, commitment])
        if self.clean_response:
            if response == None:
                raise ValueError("Transaction not found")
            return TransactionElement(response)
        return response

    def build_and_send_request(self, method, params: List[Any]) -> RPCResponse | dict[str, Any] | List[dict[str, Any]]:
        """
        Builds and sends an RPC request to the server.

        Args:
            method (str): The RPC method to call.
            params (List[Any]): The parameters to pass to the RPC method.

        Returns:
            RPCResponse: The response from the server.
        """
        data: dict[str, Any] = self.http.build_data(method=method, params=params)
        res: RPCResponse = self.http.send(data)
        if self.clean_response:
            if "error" in res:
                raise RPCRequestError(f"Failed to fetch data from RPC endpoint. Error {res['error']['code']}: {res['error']['message']}")
            
            if isinstance(res['result'], dict) or isinstance(res['result'], list) or isinstance(res['result'], str) or isinstance(res['result'], int) or res['result'] == None:
                return res['result']
            else:
                raise RPCRequestError(f"Invalid response from RPC endpoint. Expected types dict | list | str | int, got {type(res['result']).__name__}")
            
        return res

    # Non "get" methods
    def request_airdrop(
        self, public_key: PublicKey | Text, lamports: int
    ) -> RPCResponse[str] | str:
        """
        Requests an airdrop of lamports to the specified public key.

        Args:
            public_key (PublicKey | Text): The public key of the account to receive the airdrop.
            lamports (int): The amount of lamports to request in the airdrop.

        Returns:
            RPCResponse: The response from the Solana JSON RPC API.
        """
        return self.build_and_send_request("requestAirdrop", [public_key, lamports])

    def send_transaction(self, transaction: Transaction) -> RPCResponse[str] | str:
        """
        Sends a transaction to the Solana network.

        Args:
            transaction (Transaction): The transaction to send.

        Returns:
            RPCResponse: The response from the Solana network.
        """
        recent_blockhash = transaction.recent_blockhash

        if recent_blockhash is None:
            blockhash_resp = self.get_recent_blockhash()
            recent_blockhash = blockhash_resp.blockhash

        transaction.recent_blockhash = recent_blockhash
        transaction.sign()

        return self.build_and_send_request(
            "sendTransaction", [transaction.serialize(), {"encoding": "base64"}]
        )
