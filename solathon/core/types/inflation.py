from typing import TypedDict


class InflationGovernorType(TypedDict):
    """
    JSON Response type of Inflation Governer Information received by RPC
    """

    foundation: float
    foundationTerm: int
    initial: float
    taper: float
    terminal: float


class InflationGovernor:
    """
    Convert Inflation Governer Information JSON to Class
    """

    def __init__(self, response: InflationGovernorType) -> None:
        self.raw = response
        self.foundation = response["foundation"]
        self.foundation_term = response["foundationTerm"]
        self.initial = response["initial"]
        self.taper = response["taper"]
        self.terminal = response["terminal"]

    def __repr__(self) -> str:
        return f"InflationGovernor(foundation={self.foundation!r}, foundation_term={self.foundation_term!r}, initial={self.initial!r}, taper={self.taper!r}, terminal={self.terminal!r})"


class InflationRateType(TypedDict):
    """
    JSON Response type of Inflation Rate Information received by RPC
    """

    epoch: int
    foundation: float
    validator: float
    total: float


class InflationRate:
    def __init__(self, response: InflationRateType) -> None:
        self.raw = response
        self.epoch = response["epoch"]
        self.foundation = response["foundation"]
        self.validator = response["validator"]
        self.total = response["total"]

    def __repr__(self) -> str:
        return f"InflationRate(epoch={self.epoch!r}, foundation={self.foundation!r}, validator={self.validator!r}, total={self.total!r})"


class InflationRewardType(TypedDict):
    """
    JSON Response type of Inflation Reward Information received by RPC
    """

    epoch: int
    effectiveSlot: int
    amount: int
    postBalance: int
    commission: int | None


class InflationReward:
    """
    Convert Inflation Reward Information JSON to Class
    """

    def __init__(self, response: InflationRewardType) -> None:
        self.raw = response
        self.epoch = response["epoch"]
        self.effective_slot = response["effectiveSlot"]
        self.amount = response["amount"]
        self.post_balance = response["postBalance"]
        self.commission = response.get("commission")

    def __repr__(self) -> str:
        return f"InflationReward(epoch={self.epoch!r}, effective_slot={self.effective_slot!r}, amount={self.amount!r})"
