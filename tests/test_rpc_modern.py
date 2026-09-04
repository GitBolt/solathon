import asyncio
import inspect
import json

import httpx
import pytest

from solathon.async_client import AsyncClient
from solathon.client import Client
from solathon.core.http import RequestBuilder
from solathon.core.instructions import transfer
from solathon.core.types import BlockHash
from solathon.publickey import PublicKey
from solathon.transaction import Transaction
from solathon.utils import RPCRequestError


def test_request_builder_always_emits_params_and_encodes_bytes():
    builder = RequestBuilder()

    assert builder.build_data("getHealth")["params"] == []
    assert builder.build_data("getHealth", [None])["params"] == []
    assert builder.build_data("example", [{"payload": b"abc"}])["params"] == [
        {"payload": "YWJj"}
    ]


def test_injected_sync_http_client_preserves_envelope_and_ownership():
    expected = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"context": {"slot": 99}, "value": "ok", "extra": True},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["params"] == []
        return httpx.Response(200, json=expected)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = Client(
        "https://rpc.example",
        clean_response=False,
        http_client=http_client,
    )

    assert client.get_health() == expected
    client.close()
    assert not http_client.is_closed
    http_client.close()


def test_rpc_error_keeps_code_and_data():
    def handler(request: httpx.Request) -> httpx.Response:
        request_id = json.loads(request.content)["id"]
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32002,
                    "message": "transaction failed",
                    "data": {"logs": ["program log"]},
                },
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = Client("https://rpc.example", http_client=http_client)
    with pytest.raises(RPCRequestError) as caught:
        client.get_health()
    assert caught.value.code == -32002
    assert caught.value.data == {"logs": ["program log"]}
    assert caught.value.error["message"] == "transaction failed"
    assert caught.value.response["error"] is caught.value.error
    http_client.close()


def test_batch_results_are_reordered_to_match_requests():
    def handler(request: httpx.Request) -> httpx.Response:
        batch = json.loads(request.content)
        responses = [
            {"jsonrpc": "2.0", "id": item["id"], "result": item["method"]}
            for item in reversed(batch)
        ]
        return httpx.Response(200, json=responses)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = Client("https://rpc.example", http_client=http_client)
    assert client.send_batch([("first", None), ("second", [])]) == [
        "first",
        "second",
    ]
    assert client.send_batch([]) == []
    http_client.close()


def test_current_config_fields_and_official_multiple_account_limit():
    client = Client("http://localhost", clean_response=False)
    client.build_and_send_request = lambda method, params=None: (method, params)
    try:
        assert client.get_account_info(
            "owner",
            "confirmed",
            encoding="base64+zstd",
            data_slice={"offset": 4, "length": 8},
            min_context_slot=50,
        ) == (
            "getAccountInfo",
            [
                "owner",
                {
                    "encoding": "base64+zstd",
                    "commitment": "confirmed",
                    "dataSlice": {"offset": 4, "length": 8},
                    "minContextSlot": 50,
                },
            ],
        )
        assert client.get_blocks(10, commitment="confirmed", min_context_slot=9) == (
            "getBlocks",
            [10, None, {"commitment": "confirmed", "minContextSlot": 9}],
        )
        with pytest.raises(ValueError):
            client.get_multiple_accounts([])
        with pytest.raises(ValueError):
            client.get_multiple_accounts(["key"] * 101)
    finally:
        client.http.client.close()


def test_binary_block_and_transaction_payloads_pass_through():
    client = Client("http://localhost")
    payload = {"slot": 1, "transaction": ["encoded", "base64"]}
    client.build_and_send_request = lambda method, params=None: payload
    try:
        assert client.get_transaction("signature", encoding="base64") is payload
        assert client.get_block(1, encoding="base64") is payload
        assert client.get_block(1, transaction_details="accounts") is payload
        assert client.get_block(1, transaction_details="signatures") is payload
        assert client.get_block(1, transaction_details="none") is payload
    finally:
        client.http.client.close()


def test_simulation_can_serialize_an_unsigned_transaction_when_not_verifying():
    payer = PublicKey(bytes(range(32)))
    transaction = Transaction(
        fee_payer=payer,
        signers=[payer],
        recent_blockhash=str(PublicKey(bytes(range(32, 64)))),
        instructions=[transfer(payer, PublicKey(bytes(range(64, 96))), 1)],
    )
    client = Client("http://localhost")
    captured = {}

    def request(method, params=None):
        captured["method"] = method
        captured["params"] = params
        return {"value": {"err": None}}

    client.build_and_send_request = request
    try:
        assert client.simulate_transaction(transaction) == {"err": None}
        assert captured["method"] == "simulateTransaction"
        assert isinstance(captured["params"][0], bytes)
        assert captured["params"][1]["sigVerify"] is False

        with pytest.raises(ValueError, match="missing"):
            client.simulate_transaction(transaction, sig_verify=True)
    finally:
        client.http.client.close()


def test_replace_recent_blockhash_simulation_stays_offline_and_matches_async():
    payer = PublicKey(bytes(range(32)))

    def transaction() -> Transaction:
        return Transaction(
            fee_payer=payer,
            signers=[payer],
            instructions=[transfer(payer, PublicKey(bytes(range(64, 96))), 1)],
        )

    async def run_test() -> None:
        sync_client = Client("http://localhost")
        async_client = AsyncClient("http://localhost")
        sync_capture = {}
        async_capture = {}

        def unexpected_sync_blockhash(*args, **kwargs):
            raise AssertionError("replaceRecentBlockhash must not fetch a blockhash")

        async def unexpected_async_blockhash(*args, **kwargs):
            raise AssertionError("replaceRecentBlockhash must not fetch a blockhash")

        def sync_request(method, params=None):
            sync_capture["request"] = (method, params)
            return {"value": {"err": None}}

        async def async_request(method, params=None):
            async_capture["request"] = (method, params)
            return {"value": {"err": None}}

        sync_client.get_latest_blockhash = unexpected_sync_blockhash
        async_client.get_latest_blockhash = unexpected_async_blockhash
        sync_client.build_and_send_request = sync_request
        async_client.build_and_send_request = async_request
        try:
            sync_transaction = transaction()
            async_transaction = transaction()
            assert sync_client.simulate_transaction(
                sync_transaction, replace_recent_blockhash=True
            ) == {"err": None}
            assert await async_client.simulate_transaction(
                async_transaction, replace_recent_blockhash=True
            ) == {"err": None}
            assert sync_transaction.recent_blockhash == (
                "11111111111111111111111111111111"
            )
            assert async_transaction.recent_blockhash == (
                "11111111111111111111111111111111"
            )
            assert async_capture["request"] == sync_capture["request"]
        finally:
            sync_client.http.client.close()
            await async_client.http.client.aclose()

    asyncio.run(run_test())


def test_inflation_reward_retains_none_positions():
    reward = {
        "epoch": 2,
        "effectiveSlot": 10,
        "amount": 3,
        "postBalance": 100,
        "commission": None,
    }
    client = Client("http://localhost")
    client.build_and_send_request = lambda method, params=None: [None, reward]
    try:
        result = client.get_inflation_reward(["first", "second"])
        assert result[0] is None
        assert result[1].raw == reward
    finally:
        client.http.client.close()


def test_all_token_accounts_queries_both_programs_and_retains_owner():
    client = Client("http://localhost")
    seen = {}
    owners = [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    ]

    def batch(requests):
        seen["requests"] = requests
        return [
            {
                "value": [
                    {
                        "pubkey": f"account-{index}",
                        "account": {
                            "lamports": 1,
                            "owner": owner,
                            "executable": False,
                            "rentEpoch": 0,
                            "data": {},
                        },
                    }
                ]
            }
            for index, owner in enumerate(owners)
        ]

    client.send_batch = batch
    try:
        accounts = client.get_all_token_accounts_by_owner("wallet")
        assert [account.account.owner for account in accounts] == owners
        assert [request[1][1]["programId"] for request in seen["requests"]] == owners
    finally:
        client.http.client.close()


def test_confirm_transaction_is_commitment_and_block_height_aware():
    client = Client("http://localhost")
    statuses = iter(
        [
            [None],
            [
                {
                    "slot": 7,
                    "confirmations": 1,
                    "err": None,
                    "confirmationStatus": "confirmed",
                }
            ],
        ]
    )
    client.get_signature_statuses = lambda *args, **kwargs: next(statuses)
    client.get_block_height = lambda *args, **kwargs: 9
    try:
        status = client.confirm_transaction(
            "signature",
            commitment="confirmed",
            last_valid_block_height=10,
            timeout=None,
            poll_interval=0,
        )
        assert status["slot"] == 7

        client.get_signature_statuses = lambda *args, **kwargs: [None]
        client.get_block_height = lambda *args, **kwargs: 11
        with pytest.raises(RPCRequestError) as caught:
            client.confirm_transaction(
                "expired",
                last_valid_block_height=10,
                timeout=None,
                poll_interval=0,
            )
        assert caught.value.data == {
            "blockHeight": 11,
            "lastValidBlockHeight": 10,
        }
    finally:
        client.http.client.close()


class _FakeTransaction(Transaction):
    def __init__(self):
        self.recent_blockhash = None
        self.nonce_info = None
        self.sign_count = 0
        self.serialize_count = 0

    def sign(self, signatures=None):
        self.sign_count += 1

    def serialize(self, *args, **kwargs):
        self.serialize_count += 1
        return b"signed-once"


def test_send_and_confirm_signs_and_sends_exactly_once():
    client = Client("http://localhost")
    transaction = _FakeTransaction()
    confirmed = {}
    latest = BlockHash({"blockhash": "blockhash", "lastValidBlockHeight": 44})
    latest.context = {"slot": 40}
    client.get_latest_blockhash = lambda *args, **kwargs: latest

    def send(payload, options=None):
        confirmed["payload"] = payload
        confirmed["options"] = options
        return "signature"

    client.send_raw_transaction = send

    def confirm(signature, **kwargs):
        confirmed["signature"] = signature
        confirmed.update(kwargs)

    client.confirm_transaction = confirm
    try:
        assert client.send_and_confirm_transaction(transaction) == "signature"
        assert transaction.recent_blockhash == "blockhash"
        assert transaction.sign_count == 1
        assert transaction.serialize_count == 1
        assert confirmed["payload"] == b"signed-once"
        assert confirmed["options"] == {
            "preflightCommitment": "finalized",
            "minContextSlot": 40,
        }
        assert confirmed["last_valid_block_height"] == 44
        assert confirmed["timeout"] is None

        with pytest.raises(ValueError, match="last_valid_block_height"):
            client.send_and_confirm_transaction(transaction)
    finally:
        client.http.client.close()


def test_send_and_confirm_durable_nonce_requires_timeout_not_block_height():
    client = Client("http://localhost")
    transaction = _FakeTransaction()
    transaction.nonce_info = object()
    client.get_latest_blockhash = lambda *args, **kwargs: pytest.fail(
        "durable nonces must not fetch an unrelated recent blockhash"
    )
    client.send_raw_transaction = lambda payload, options=None: "signature"
    confirmed = {}

    def confirm(signature, **kwargs):
        confirmed.update(signature=signature, **kwargs)

    client.confirm_transaction = confirm
    try:
        with pytest.raises(ValueError, match="finite timeout"):
            client.send_and_confirm_transaction(transaction)
        with pytest.raises(ValueError, match="does not apply"):
            client.send_and_confirm_transaction(
                transaction,
                last_valid_block_height=10,
                timeout=5,
            )

        assert (
            client.send_and_confirm_transaction(transaction, timeout=5) == "signature"
        )
        assert confirmed["last_valid_block_height"] is None
        assert confirmed["timeout"] == 5
    finally:
        client.http.client.close()


def test_sync_async_public_method_sets_and_signatures_match():
    sync_methods = {
        name
        for name, value in inspect.getmembers(Client, inspect.isfunction)
        if not name.startswith("_")
    }
    async_methods = {
        name
        for name, value in inspect.getmembers(AsyncClient, inspect.isfunction)
        if not name.startswith("_")
    }
    assert sync_methods == async_methods - {"build_and_send_request_async"}

    for name in sync_methods:
        sync_signature = inspect.signature(getattr(Client, name))
        async_signature = inspect.signature(getattr(AsyncClient, name))
        sync_params = tuple(sync_signature.parameters)[1:]
        async_params = tuple(async_signature.parameters)[1:]
        assert sync_params == async_params
        assert async_signature.return_annotation == sync_signature.return_annotation

    assert (
        inspect.signature(AsyncClient.__init__).return_annotation
        is not inspect.Signature.empty
    )
    assert (
        inspect.signature(AsyncClient.build_and_send_request_async).return_annotation
        == inspect.signature(AsyncClient.build_and_send_request).return_annotation
    )


def test_async_confirmation_behavior_matches_sync():

    async def run_test():
        async_http = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: None)
        )
        client = AsyncClient("http://localhost", http_client=async_http)

        async def statuses(*args, **kwargs):
            return [
                {
                    "slot": 8,
                    "confirmations": None,
                    "err": None,
                    "confirmationStatus": "finalized",
                }
            ]

        client.get_signature_statuses = statuses
        status = await client.confirm_transaction("signature", poll_interval=0)
        assert status["slot"] == 8
        await client.close()
        assert not async_http.is_closed
        await async_http.aclose()

    asyncio.run(run_test())
