from typing import NotRequired, TypedDict


class ClusterNodeType(TypedDict):
    """
    JSON Response type of Cluster Node Information received by RPC
    """

    pubkey: str
    gossip: str | None
    tpu: str | None
    rpc: str | None
    version: str | None
    featureSet: int | None
    shredVersion: int | None
    clientId: NotRequired[int | None]
    pubsub: NotRequired[str | None]
    serveRepair: NotRequired[str | None]
    tpuForwards: NotRequired[str | None]
    tpuForwardsQuic: NotRequired[str | None]
    tpuQuic: NotRequired[str | None]
    tpuVote: NotRequired[str | None]
    tvu: NotRequired[str | None]


class ClusterNode:
    """
    Convert Cluster Node Information JSON to Class
    """

    def __init__(self, response: ClusterNodeType) -> None:
        self.raw = response
        self.pubkey = response["pubkey"]
        self.gossip = response.get("gossip")
        self.tpu = response.get("tpu")
        self.rpc = response.get("rpc")
        self.version = response.get("version")
        self.feature_set = response.get("featureSet")
        self.shred_version = response.get("shredVersion")
        self.client_id = response.get("clientId")
        self.pubsub = response.get("pubsub")
        self.serve_repair = response.get("serveRepair")
        self.tpu_forwards = response.get("tpuForwards")
        self.tpu_forwards_quic = response.get("tpuForwardsQuic")
        self.tpu_quic = response.get("tpuQuic")
        self.tpu_vote = response.get("tpuVote")
        self.tvu = response.get("tvu")

    def __repr__(self) -> str:
        return (
            f"ClusterNode(pubkey={self.pubkey!r}, tpu={self.tpu!r}, "
            f"rpc={self.rpc!r}, version={self.version!r}, "
            f"shred_version={self.shred_version!r})"
        )
