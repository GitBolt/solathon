import asyncio
import inspect

from solathon.async_client import AsyncClient
from solathon.client import Client
from solathon.core.http import HTTPClient


RPC_METHODS = {
    "get_account_info", "get_balance", "get_block", "get_block_commitment",
    "get_block_height", "get_block_production", "get_blocks",
    "get_blocks_with_limit", "get_block_time", "get_cluster_nodes",
    "get_epoch_info", "get_epoch_schedule", "get_fee_for_message",
    "get_first_available_block", "get_genesis_hash", "get_health",
    "get_highest_snapshot_slot", "get_identity", "get_inflation_governor",
    "get_inflation_rate", "get_inflation_reward", "get_largest_accounts",
    "get_latest_blockhash", "get_leader_schedule", "get_max_retransmit_slot",
    "get_max_shred_insert_slot", "get_minimum_balance_for_rent_exemption",
    "get_multiple_accounts", "get_program_accounts",
    "get_recent_performance_samples", "get_recent_prioritization_fees",
    "get_signatures_for_address", "get_signature_statuses", "get_slot",
    "get_slot_leader", "get_slot_leaders", "get_stake_minimum_delegation",
    "get_supply", "get_token_account_balance", "get_token_accounts_by_delegate",
    "get_token_accounts_by_owner", "get_token_largest_accounts",
    "get_token_supply", "get_transaction", "get_transaction_count",
    "get_version", "get_vote_accounts", "is_blockhash_valid",
    "minimum_ledger_slot", "request_airdrop", "send_transaction",
    "simulate_transaction",
}


def test_clients_cover_current_http_rpc_methods():
    for client in (Client, AsyncClient):
        methods = {
            name for name, value in inspect.getmembers(client, inspect.isfunction)
        }
        assert RPC_METHODS <= methods


def test_parameterless_request_uses_empty_params():
    http = HTTPClient("http://localhost")
    try:
        assert http.build_data("getHealth", [None])["params"] == []
    finally:
        http.client.close()


def test_current_rpc_config_shapes():
    client = Client("http://localhost", clean_response=False)
    client.build_and_send_request = lambda method, params: (method, params)
    try:
        assert client.get_block(42, "confirmed") == (
            "getBlock",
            [42, {"maxSupportedTransactionVersion": 0, "commitment": "confirmed"}],
        )
        assert client.get_vote_accounts(keep_unstaked_delinquents=True) == (
            "getVoteAccounts",
            [{"keepUnstakedDelinquents": True}],
        )
        assert client.get_transaction("signature", "confirmed") == (
            "getTransaction",
            [
                "signature",
                {
                    "encoding": "json",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        )
    finally:
        client.http.client.close()


def test_async_current_rpc_config_shape():
    async def run_test():
        client = AsyncClient("http://localhost")

        async def request(method, params):
            return method, params

        client.build_and_send_request_async = request
        try:
            assert await client.get_transaction_count("finalized") == (
                "getTransactionCount",
                [{"commitment": "finalized"}],
            )
        finally:
            await client.http.client.aclose()

    asyncio.run(run_test())
