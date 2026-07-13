from typing import Optional, TypedDict


class ClusterNodeType(TypedDict):
    '''
    JSON Response type of Cluster Node Information received by RPC
    '''
    pubkey: str
    gossip: Optional[str]
    tpu: Optional[str]
    rpc: Optional[str]
    version: Optional[str]
    featureSet: Optional[int]
    shredVersion: Optional[int]


class ClusterNode:
    '''
    Convert Cluster Node Information JSON to Class
    '''

    def __init__(self, response: ClusterNodeType) -> None:
        self.pubkey = response['pubkey']
        self.gossip = response.get('gossip')
        self.tpu = response.get('tpu')
        self.rpc = response.get('rpc')
        self.version = response.get('version')
        self.feature_set = response.get('featureSet')
        self.shred_version = response.get('shredVersion')

    def __repr__(self) -> str:
        return f"ClusterNode(pubkey={self.pubkey!r}, tpu={self.tpu!r}, rpc={self.rpc!r}, version={self.version!r},, shred_version={self.shred_version!r})"
