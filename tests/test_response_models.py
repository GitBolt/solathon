from copy import deepcopy

import pytest

from solathon import PublicKey
from solathon.core.types import RPCError, SignatureStatus, TransactionSignature
from solathon.core.types.account_info import AccountInfo
from solathon.core.types.block import Block, TransactionElement
from solathon.core.types.cluster_node import ClusterNode
from solathon.utils import RPCRequestError, clean_response, unwrap_rpc_response


def test_account_info_uses_current_space_field_and_preserves_raw() -> None:
    payload = {
        "lamports": 5,
        "owner": "11111111111111111111111111111111",
        "executable": False,
        "rentEpoch": 0,
        "space": 128,
        "data": ["", "base64"],
        "futureField": "kept",
    }

    account = AccountInfo(payload)

    assert account.space == 128
    assert account.size == 128
    assert account.raw["futureField"] == "kept"


def test_transaction_model_preserves_v0_v1_and_additive_metadata() -> None:
    key = "11111111111111111111111111111111"
    payload = {
        "slot": 10,
        "blockTime": None,
        "version": 1,
        "transaction": {
            "signatures": [key],
            "message": {
                "header": {
                    "numRequiredSignatures": 1,
                    "numReadonlySignedAccounts": 0,
                    "numReadonlyUnsignedAccounts": 0,
                },
                "accountKeys": [
                    {
                        "pubkey": key,
                        "signer": True,
                        "writable": True,
                        "source": "transaction",
                    }
                ],
                "recentBlockhash": key,
                "instructions": [],
                "addressTableLookups": [],
                "transactionConfig": {
                    "computeUnitLimit": 200_000,
                    "loadedAccountsDataSizeLimit": 64_000,
                },
            },
        },
        "meta": {
            "err": None,
            "fee": 5_000,
            "preBalances": [10_000],
            "postBalances": [5_000],
            "loadedAddresses": {"writable": [], "readonly": []},
            "computeUnitsConsumed": 1_234,
            "costUnits": 1_300,
            "loadedAccountsDataSize": 256,
            "futureMeta": {"kept": True},
        },
    }

    transaction = TransactionElement(payload)

    assert transaction.version == 1
    assert (
        transaction.transaction.message.transaction_config["computeUnitLimit"]
        == 200_000
    )
    assert transaction.transaction.message.is_account_signer(0)
    assert transaction.transaction.message.is_account_writable(0)
    assert transaction.meta.raw["futureMeta"] == {"kept": True}
    assert transaction.raw is payload


def test_block_model_preserves_signature_only_and_nullable_current_fields() -> None:
    block = Block(
        {
            "blockHeight": None,
            "blockTime": None,
            "blockhash": str(PublicKey(bytes([7]) * 32)),
            "parentSlot": 9,
            "previousBlockhash": str(PublicKey(bytes([8]) * 32)),
            "signatures": ["signature"],
            "numRewardPartitions": None,
        }
    )

    assert block.block_height is None
    assert block.signatures == ["signature"]
    assert block.num_reward_partitions is None


def test_cluster_node_preserves_current_optional_service_endpoints() -> None:
    node = ClusterNode(
        {
            "pubkey": str(PublicKey(bytes([9]) * 32)),
            "gossip": "127.0.0.1:8001",
            "tpu": "127.0.0.1:8003",
            "rpc": "127.0.0.1:8899",
            "version": "4.2.2",
            "featureSet": 123,
            "shredVersion": 456,
            "pubsub": "127.0.0.1:8900",
            "serveRepair": "127.0.0.1:8002",
            "tpuForwards": "127.0.0.1:8004",
            "tpuForwardsQuic": "127.0.0.1:8006",
            "tpuQuic": "127.0.0.1:8009",
            "tpuVote": "127.0.0.1:8005",
            "tvu": "127.0.0.1:8000",
        }
    )

    assert node.pubsub == "127.0.0.1:8900"
    assert node.serve_repair == "127.0.0.1:8002"
    assert node.tpu_forwards == "127.0.0.1:8004"
    assert node.tpu_forwards_quic == "127.0.0.1:8006"
    assert node.tpu_quic == "127.0.0.1:8009"
    assert node.tpu_vote == "127.0.0.1:8005"
    assert node.tvu == "127.0.0.1:8000"


def test_status_models_tolerate_nullable_and_additive_fields() -> None:
    status = SignatureStatus(
        {
            "slot": 4,
            "confirmations": None,
            "err": None,
            "confirmationStatus": None,
            "future": 1,
        }
    )
    signature = TransactionSignature(
        {
            "signature": "sig",
            "slot": 4,
            "err": None,
            "memo": None,
            "blockTime": None,
            "confirmationStatus": None,
            "future": 2,
        }
    )

    assert status.confirmation_status is None
    assert status.raw["future"] == 1
    assert signature.raw["future"] == 2


def test_rpc_errors_retain_code_message_and_data() -> None:
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32015, "message": "unsupported version", "data": {"x": 1}},
    }

    error = RPCError(response["error"])
    assert error.code == -32015
    assert error.data == {"x": 1}
    with pytest.raises(RPCRequestError) as caught:
        unwrap_rpc_response(response)
    assert caught.value.code == -32015
    assert caught.value.data == {"x": 1}


def test_clean_response_does_not_mutate_the_rpc_payload() -> None:
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"context": {"slot": 1, "apiVersion": "4.2.2"}, "value": 5},
    }
    original = deepcopy(response)

    assert clean_response(response) == 5
    assert response == original
