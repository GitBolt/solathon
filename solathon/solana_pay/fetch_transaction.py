from solathon.client import Client
from solathon.core.types.block import BlockHash, BlockHashType
from solathon.publickey import PublicKey
from solathon.core.types import Commitment, RPCResponse
from solathon.transaction import Transaction

from typing import Optional
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import httpx
import json


def fetch_transaction(client: Client, account: PublicKey, link: str, commitment: Optional[Commitment] = None) -> Transaction:
    '''
    Fetches a transaction from a Solana Pay transaction link.

    Args:
        client (Client): A connection client to the cluster.
        account (PublicKey): Account that may sign the transaction.
        link (str): [Solana Pay Spec](https://github.com/solana-labs/solana-pay/blob/master/SPEC.md#link) link to fetch the transaction from.
        commitment (Commitment, optional): Commitment option for `getLatestBlockhash`.

    Raises:
        ValueError: If `transaction` is not found in the response.

    :type client: solathon.client.Client
    :type account: solathon.publickey.PublicKey
    :type commitment: solathon.core.types.Commitment
    :rtype: solathon.transaction.Transaction
    '''
    http = httpx.Client()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Prepare data for the request
    data = json.dumps({'account': account.byte_value})
    
    # Make the HTTP request
    response = http.post(url=link, headers=headers, data=data)
    json_data = response.json()

    # Check if the transaction is found in the response
    if not json_data.get("transaction"):
        raise ValueError("Transaction not found")

    # Ensure the transaction is a valid string
    if not isinstance(json_data['transaction'], str):
        raise ValueError("Invalid Transaction")

    # Deserialize the transaction from hex
    transaction: Transaction = Transaction.from_buffer(
        bytes.fromhex(json_data['transaction']))

    # Verify transaction signatures
    for signature in transaction.signatures:
        if not signature.signature:
            raise ValueError("Missing Signature")

        # Verify the signature using nacl library
        public_key = VerifyKey(signature.public_key)
        try:
            public_key.verify(signature.signature)
        except BadSignatureError:
            raise ValueError("Invalid Signature")

    # Additional transaction checks
    if len(transaction.signatures) == 1 and transaction.signatures[0].public_key == account:
        if not transaction.recent_blockhash:
            # Fetch recent blockhash if missing
            raw_blockhash: RPCResponse[BlockHashType] = client.get_latest_blockhas(commitment=commitment)
            transaction.recent_blockhash = BlockHash(raw_blockhash['result']['value']).blockhash
    if not transaction.signatures:
        fee_payer = account
    elif fee_payer not in transaction.signatures:
         raise ValueError("Invalid Fee payer or Missing Signature")
    return transaction
