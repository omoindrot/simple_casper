import random


class Vote():
    """Vote message

    Args:
        source: hash of the source block
        target: hash of the target block
        epoch_source: epoch of the source block
        epoch_target: epoch of the target block
        sender: node sending the VOTE message
    """
    def __init__(self, source, target, epoch_source, epoch_target, sender):
        self.hash = random.randint(1, 10**30)
        self.source = source
        self.target = target
        self.epoch_source = epoch_source
        self.epoch_target = epoch_target
        self.sender = sender
