from solathon.client import Client
from solathon.core.types import Commitment
from solathon.core.types.block import TransactionElement
from solathon.solana_pay.types import CreateTransferFields
from solathon.transaction import Transaction
from solathon.utils import LAMPORT_PER_SOL

from typing import Optional


def validate_transfer(client: Client, signature: str, transfer_fields: CreateTransferFields, commitment: Optional[Commitment] = None) -> TransactionElement:
    '''
    Check that a given transaction contains a valid Solana Pay transfer.

    Args
        client (Client) - A connection client to the cluster.
        signature (str) - Signature of the transaction to validate.
        transfer_fields (CreateTransferFields) - Fields of a Solana Pay transfer request URL.
        commitment (Commitment, optional) - commitment option for `getTransaction`.

    Raises
        ValueError - If `recipient` or `amount` is missing from `transfer_fields`.

    :type client: solathon.client.Client
    :type transfer_fields: solathon.solana_pay.types.CreateTransferFields
    :type commitment: solathon.core.types.Commitment
    :rtype: solathon.core.types.block.TransactionElement
    '''
    response: TransactionElement = None
    if client.clean_response == False:
        raw_response = client.get_transaction(signature, commitment)
        response = TransactionElement(raw_response)
    else:
        response = client.get_transaction(signature, commitment)

    if not response:
        raise ValueError("Transaction not found")

    message = response.transaction.message
    signatures = response.transaction.signatures

    if not response.meta:
        raise ValueError("Transaction meta not found")

    if response.meta.err:
        raise ValueError(f"Meta failed with error: {response.meta.err}")

    transaction: Transaction = Transaction.populate(message, signatures)
    instructions = transaction.instructions[:]
    instruction = instructions.pop()
    if not instruction:
        raise ValueError("Instruction not found")

    if transfer_fields.get("recipient", None) == None:
        raise ValueError("Recipient is missing from transfer_fields")

    try:
        acc_index = message.account_keys.index(transfer_fields['recipient'])
    except ValueError:
        raise ValueError("Recipient not found in transaction")

    if transfer_fields.get("references", None) != None:
        _from, _to, *extra_keys = instruction.keys
        if len(extra_keys) != len(transfer_fields['references']):
            raise ValueError("Invalid number of references")

        for index, reference in enumerate(transfer_fields['references']):
            if str(extra_keys[index].public_key) != str(reference):
                raise ValueError(f"Invalid reference {index}")

    pre_balance = response.meta.pre_balances[acc_index] / LAMPORT_PER_SOL
    post_balance = response.meta.post_balances[acc_index] / LAMPORT_PER_SOL

    if (post_balance - pre_balance + 0.0000005001) < transfer_fields['amount']:
        raise ValueError("Amount not transferred to recipient")

    # if transfer_fields.get("memo", None) != None:
    #     instruction = instructions.pop()
    #     if not instruction:
    #         raise ValueError("Missing memo instruction")
    #     if len(instruction.keys):
    #         raise ValueError("Invalid memo keys")
    #     if instruction.data.decode('utf-8') != transfer_fields['memo']:
    #         raise ValueError("Invalid memo")

    return response
