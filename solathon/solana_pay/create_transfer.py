from solathon.client import Client
from solathon.core.instructions import AccountMeta, transfer
from solathon.core.layouts import SYSTEM_PROGRAM_ID
from solathon.core.types import Commitment, RPCResponse
from solathon.core.types.account_info import AccountInfo, AccountInfoType
from solathon.core.types.block import BlockHash, BlockHashType
from solathon.keypair import Keypair
from solathon.publickey import PublicKey
from solathon.solana_pay.types import CreateTransferFields
from solathon.transaction import Transaction
from solathon.utils import RPCRequestError, sol_to_lamport

from typing import Optional


def create_transfer(client: Client,  sender: Keypair, transfer_fields: CreateTransferFields, commitment: Optional[Commitment] = None) -> Transaction:
    """
    Creates and returns a Solana Pay transfer transaction.

    Args
        client (Client) - A connection client to the cluster.
        sender (Keypair) - Account that will send the transfer.
        transfer_fields (CreateTransferFields) - Fields of a Solana Pay transfer request URL.
        commitment (Commitment, optional) - commitment option for `getRecentBlockhash`.

    Raises
        ValueError - If `recipient` or `amount` is missing from `transfer_fields`.

    :type client: solathon.client.Client
    :type sender: solathon.publickey.PublicKey
    :type transfer_fields: solathon.solana_pay.types.CreateTransferFields
    :type commitment: solathon.core.types.Commitment
    :rtype: solathon.transaction.Transaction
    """

    sender_info: AccountInfo = None
    if client.clean_response == False:
        raw_sender_info: RPCResponse[AccountInfoType] = client.get_account_info(
            sender.public_key)
        if raw_sender_info['result']['value'] == None:
            raise RPCRequestError(
                f"Account details not found: {sender.public_key}")
        sender_info = AccountInfo(raw_sender_info['result']['value'])
    else:
        sender_info: AccountInfo = client.get_account_info(sender.public_key)

    if sender_info.owner != str(SYSTEM_PROGRAM_ID):
        raise ValueError("Invalid sender account")
    if sender_info.executable:
        raise ValueError("Sender account is executable")

    if transfer_fields.get("recipient", None) == None:
        raise ValueError("Recipient is missing from transfer_fields")
    
    if not isinstance(transfer_fields['recipient'], PublicKey):
        raise ValueError(f"Invalid `recipient` type, found {type(transfer_fields['recipient']).__name__} must be of type PublicKey")

    recipient: AccountInfo = None
    if client.clean_response == False:
        raw_recipient: RPCResponse[AccountInfoType] = client.get_account_info(
            transfer_fields['recipient'])
        if raw_recipient['result']['value'] == None:
            raise RPCRequestError(
                f"Account details not found: {transfer_fields['recipient']}")
        recipient = AccountInfo(raw_recipient['result']['value']['owner'])
    else:
        recipient: AccountInfo = client.get_account_info(
            transfer_fields['recipient'])

    if recipient.owner != str(SYSTEM_PROGRAM_ID):
        raise ValueError("Invalid recipient account")
    if recipient.executable:
        raise ValueError("Recipient account is executable")

    if transfer_fields.get("amount", None) == None:
        raise ValueError("Amount is missing from transfer_fields")

    if not isinstance(transfer_fields['amount'], float) and not isinstance(transfer_fields['amount'], int):
        raise ValueError(f"Invalid `amount` type, found {type(transfer_fields['amount']).__name__} must be of type float or int")
    
    lamports = sol_to_lamport(transfer_fields['amount'])

    if lamports > sender_info.lamports:
        raise ValueError("Insufficient funds in sender account")

    instruction = transfer(
        from_public_key=sender.public_key, to_public_key=transfer_fields['recipient'], lamports=lamports)

    if transfer_fields.get("reference", None) != None:
        if isinstance(transfer_fields['reference'], list):
            for ref in transfer_fields['reference']:

                acc_ref = AccountMeta(
                    public_key=ref,
                    is_signer=False,
                    is_writable=False
                )
                instruction.keys.append(acc_ref)
        else:
            acc_ref = AccountMeta(
                public_key=transfer_fields['reference'],
                is_signer=False,
                is_writable=False
            )
            instruction.keys.append(acc_ref)

    block_hash: BlockHash = None
    if client.clean_response == False:
        raw_block_hash: RPCResponse[BlockHashType] = client.get_latest_blockhash(
            commitment=commitment)
        block_hash: BlockHash = BlockHash(raw_block_hash['result']['value'])
    else:
        block_hash: BlockHash = client.get_latest_blockhash(
            commitment=commitment)

    transaction = Transaction(instructions=[instruction], signers=[
                              sender], fee_payer=sender.public_key, recent_blockhash=block_hash.blockhash)

    return transaction
