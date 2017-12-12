import random

from parameters import *


class Block():
    """One node (roundrobin) adds a new block to the blockchain every
    BLOCK_PROPOSAL_TIME iterations.

    Args:
        parent: parent block
        finalized_dynasties: dynasties which have been finalized.
                             Only a committed block's dynasty becomes finalized.
    """
    def __init__(self, parent=None, finalized_dynasties=None):
        """A block contains the following arguments:

        self.hash: hash of the block
        self.height: height of the block (genesis = 0)
        self.prev_hash: hash of the parent block
        self.prev_dynasty: previous dynasty (2/3 have to commit)
        self.current_dynasty: current dynasty (2/3 have to commit)
        self.next_dynasty: next dynasty

        The block needs to be signed by both the previous and current dynasties.
        The next dynasty is decided at this block so that it is public.
        """
        self.hash = random.randint(1, 10**30)
        # If we are genesis block, set initial values
        if not parent:
            self.height = 0
            self.prev_hash = 0
            self.prev_dynasty = self.current_dynasty = Dynasty(INITIAL_VALIDATORS)
            self.next_dynasty = self.generate_next_dynasty(self.current_dynasty.id)
            return
        # Set our block height and our prev_hash
        self.height = parent.height + 1
        self.prev_hash = parent.hash
        # Generate a random next dynasty
        self.next_dynasty = self.generate_next_dynasty(parent.current_dynasty.id)
        # If the current_dynasty was finalized, we advance to the next dynasty
        if parent.current_dynasty in finalized_dynasties:
            self.prev_dynasty = parent.current_dynasty
            self.current_dynasty = parent.next_dynasty
            return
        # `current_dynasty` has not yet been finalized so we don't rotate validators
        self.prev_dynasty = parent.prev_dynasty
        self.current_dynasty = parent.current_dynasty

    @property
    def epoch(self):
        return self.height // EPOCH_SIZE

    def generate_next_dynasty(self, prev_dynasty_id):
        # Fix the seed so that every validator can generate the same dynasty
        random.seed(self.hash)
        next_dynasty = Dynasty(random.sample(VALIDATOR_IDS, NUM_VALIDATORS), prev_dynasty_id + 1)

        # Remove the seed for other operations
        random.seed()
        return next_dynasty


class Dynasty():
    """A Dynasty is a certain set of validators.

    It will represent the set of valid validators for a certain block.

    Args:
        validators: set of validators in the dynasty
        id: id of the dynasty
    """
    def __init__(self, validators, id_=0):
        self.validators = validators
        self.id = id_

    def __hash__(self):
        return hash(str(self.id) + str(self.validators))

    def __eq__(self, other):
        return (str(self.id) + str(self.validators)) == \
               (str(other.id) + str(other.validators))
