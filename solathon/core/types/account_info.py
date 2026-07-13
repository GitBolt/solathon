from typing import Any, TypedDict, Union, Dict

class AccountInfoType(TypedDict):
    '''
    JSON Response type of Account Information received by RPC
    '''
    lamports: int
    owner: str
    executable: bool
    rentEpoch: int
    size: Union[int, None]
    data: Union[str, Dict[str, Any]]

    def __repr__(self) -> str:
        return f"AccountInfoType(owner={self.owner!r})"

class AccountInfo():
    '''
    Convert Account Information JSON to Class
    '''
    def __init__(self, result: AccountInfoType) -> None:
        self.lamports = result['lamports']
        self.owner = result['owner']
        self.executable = result['executable']
        self.rent_epoch = result['rentEpoch']
        self.size = result.get('space', result.get('size'))
        self.data = result['data']

    def __repr__(self) -> str:
        return f"AccountInfo(owner={self.owner!r})"

class ProgramAccountType(TypedDict):
    '''
    JSON Response type of Program Account Information received by RPC
    '''
    pubkey: str
    account: AccountInfoType

class ProgramAccount:
    '''
    Convert Program Account Information JSON to Class
    '''
    def __init__(self, result: ProgramAccountType) -> None:
        self.pubkey = result['pubkey']
        self.account = AccountInfo(result['account'])

    def __repr__(self) -> str:
        return f"ProgramAccount(pubkey={self.pubkey!r})"
