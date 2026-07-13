from typing import Optional, TypedDict


class EpochType(TypedDict):
    '''
    JSON Response type of Epoch Information received by RPC
    '''
    epoch: int
    absoluteSlot: int
    blockHeight: int
    slotIndex: int
    slotsInEpoch: int
    transactionCount: Optional[int]


class Epoch:
    '''
    Convert Epoch Information JSON to Class
    '''

    def __init__(self, response: EpochType) -> None:
        self.epoch = response['epoch']
        self.absolute_slot = response['absoluteSlot']
        self.block_height = response['blockHeight']
        self.slot_index = response['slotIndex']
        self.slots_in_epoch = response['slotsInEpoch']
        self.transaction_count = response.get('transactionCount')

    def __repr__(self) -> str:
        return f"Epoch(epoch={self.epoch!r}, absolute_slot={self.absolute_slot!r}, block_height={self.block_height!r}, slot_index={self.slot_index!r})"


class EpochScheduleType(TypedDict):
    '''
    JSON Response type of Epoch Schedule Information received by RPC
    '''
    slotsPerEpoch: int
    leaderScheduleSlotOffset: int
    warmup: bool
    firstNormalEpoch: int
    firstNormalSlot: int


class EpochSchedule:
    '''
    Convert Epoch Schedule Information JSON to Class
    '''

    def __init__(self, response: EpochScheduleType) -> None:
        self.slots_per_epoch = response['slotsPerEpoch']
        self.leader_schedule_slot_offset = response['leaderScheduleSlotOffset']
        self.warmup = response['warmup']
        self.first_normal_epoch = response['firstNormalEpoch']
        self.first_normal_slot = response['firstNormalSlot']

    def __repr__(self) -> str:
        return f"EpochSchedule(slots_per_epoch={self.slots_per_epoch!r}, leader_schedule_slot_offset={self.leader_schedule_slot_offset!r}, warmup={self.warmup!r})"
