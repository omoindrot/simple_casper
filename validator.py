from block import Block, Dynasty
from message import Vote
from parameters import *

# Root of the blockchain
ROOT = Block()

class Validator(object):
    """Abstract class for validators."""

    def __init__(self, network, id):
        # processed blocks
        self.processed = {ROOT.hash: ROOT}
        # Messages that are not processed yet, and require another message
        # to be processed
        # Dict from hash of dependency to object that can be processed
        # when dependency is processed
        # Example:
        # prepare messages processed before block is processed
        # commit messages processed before we reached 2/3 prepares
        self.dependencies = {}
        # Set of finalized dynasties
        self.finalized_dynasties = set()
        self.finalized_dynasties.add(Dynasty(INITIAL_VALIDATORS))
        # My current epoch
        self.current_epoch = 0
        # Network I am connected to
        self.network = network
        network.nodes.append(self)
        # Tails are for checkpoint blocks, the tail is the last block
        # (before the next checkpoint) following the checkpoint
        self.tails = {ROOT.hash: ROOT}
        # Closest checkpoint ancestor for each block
        self.tail_membership = {ROOT.hash: ROOT.hash}
        self.id = id

    # If we processed an object but did not receive some dependencies
    # needed to process it, save it to be processed later
    def add_dependency(self, hash_, obj):
        if hash_ not in self.dependencies:
            self.dependencies[hash_] = []
        self.dependencies[hash_].append(obj)

    # Get the checkpoint immediately before a given checkpoint
    def get_checkpoint_parent(self, block):
        if block.height == 0:
            return None
        return self.processed[self.tail_membership[block.prev_hash]]

    def is_ancestor(self, anc, desc):
        """Is a given checkpoint an ancestor of another given checkpoint?
        Args:
            anc: ancestor block (or block hash)
            desc: descendant block (or block hash)
        """
        # if anc or desc are block hashes, we can get the blocks from self.processed
        # TODO: but what if they are not in processed? BUG?
        if not isinstance(anc, Block):
            anc = self.processed[anc]
        if not isinstance(desc, Block):
            desc = self.processed[desc]
        # Check that the blocks are both checkpoints
        assert anc.height % EPOCH_SIZE == 0
        assert desc.height % EPOCH_SIZE == 0
        while True:
            if desc is None:
                return False
            if desc.hash == anc.hash:
                return True
            desc = self.get_checkpoint_parent(desc)

    # Called every round
    def tick(self, time):
        # At time 0: validator 0
        # At time BLOCK_PROPOSAL_TIME: validator 1
        # .. At time NUM_VALIDATORS * BLOCK_PROPOSAL_TIME: validator 0
        if self.id == (time // BLOCK_PROPOSAL_TIME) % NUM_VALIDATORS and time % BLOCK_PROPOSAL_TIME == 0:
            # One node is authorized to create a new block and broadcast it
            new_block = Block(self.head, self.finalized_dynasties)
            self.network.broadcast(new_block)
            self.on_receive(new_block)  # immediately "receive" the new block (no network latency)

class VoteValidator(Validator):
    """Add the vote messages + slashing conditions capability"""

    def __init__(self, network, id):
        super(VoteValidator, self).__init__(network, id)
        # the head is the latest block processed descendant of the highest
        # justified checkpoint
        self.head = ROOT
        self.highest_justified_checkpoint = ROOT
        self.main_chain_size = 1

        # Set of justified block hashes
        self.justified = {ROOT.hash}

        # Set of finalized block hashes
        self.finalized = {ROOT.hash}

        # Map {sender -> votes}
        # Contains all the votes, and allow us to see who voted for whom
        # Used to check for the slashing conditions
        self.votes = {}

        # Map {source_hash -> {target_hash -> count}} to count the votes
        # ex: self.vote_count[source][target] will be between 0 and NUM_VALIDATORS
        self.vote_count = {}

    # TODO: we could write function is_justified only based on self.processed and self.votes
    #       (note that the votes are also stored in self.processed)
    def is_justified(self, _hash):
        """Returns True if the `_hash` corresponds to a justified checkpoint.

        A checkpoint c is justified if there exists a supermajority link (c' -> c) where
        c' is justified. The genesis block is justified.
        """
        # Check that the function is called only on checkpoints
        assert _hash in self.processed, "Couldn't find block hash %d" % _hash
        assert self.processed[_hash].height % EPOCH_SIZE == 0, "Block is not a checkpoint"

        return _hash in self.justified

    def is_finalized(self, _hash):
        """Returns True if the `_hash` corresponds to a justified checkpoint.

        A checkpoint c is justified if there exists a supermajority link (c' -> c) where
        c' is justified. The genesis block is justified.
        """
        # Check that the function is called only on checkpoints
        assert _hash in self.processed, "Couldn't find block hash %d" % _hash
        assert self.processed[_hash].height % EPOCH_SIZE == 0, "Block is not a checkpoint"

        return _hash in self.finalized

    @property
    def head(self):
        return self._head

    @head.setter
    def head(self, value):
        self._head = value

    def accept_block(self, block):
        """Called on receiving a block

        Args:
            block: block processed

        Returns:
            True if block was accepted or False if we are missing dependencies
        """
        # If we didn't receive the block's parent yet, wait
        if block.prev_hash not in self.processed:
            self.add_dependency(block.prev_hash, block)
            return False

        # We receive the block
        self.processed[block.hash] = block

        # If it's an epoch block (in general)
        if block.height % EPOCH_SIZE == 0:
            #  Start a tail object for it
            self.tail_membership[block.hash] = block.hash
            self.tails[block.hash] = block
            # Maybe vote
            self.maybe_vote_last_checkpoint(block)

        # Otherwise...
        else:
            # See if it's part of the longest tail, if so set the tail accordingly
            assert block.prev_hash in self.tail_membership
            # The new block is in the same tail as its parent
            self.tail_membership[block.hash] = self.tail_membership[block.prev_hash]
            # If the block has the highest height, it becomes the end of the tail
            if block.height > self.tails[self.tail_membership[block.hash]].height:
                self.tails[self.tail_membership[block.hash]] = block

        # Reorganize the head
        self.check_head(block)
        return True

    def check_head(self, block):
        """Reorganize the head to stay on the chain with the highest
        justified checkpoint.

        If we are on wrong chain, reset the head to be the highest descendent
        among the chains containing the highest justified checkpoint.

        Args:
            block: latest block processed."""

        # we are on the right chain, the head is simply the latest block
        if self.is_ancestor(self.highest_justified_checkpoint,
                            self.tail_membership[block.hash]):
            self.head = block
            self.main_chain_size += 1

        # otherwise, we are not on the right chain
        else:
            # Find the highest descendant of the highest justified checkpoint
            # and set it as head
            # print('Wrong chain, reset the chain to be a descendant of the '
                  # 'highest justified checkpoint.')
            max_height = self.highest_justified_checkpoint.height
            max_descendant = self.highest_justified_checkpoint.hash
            for _hash in self.tails:
                # if the tail is descendant to the highest justified checkpoint
                # TODO: bug with is_ancestor? see higher
                if self.is_ancestor(self.highest_justified_checkpoint, _hash):
                    new_height = self.processed[_hash].height
                    if new_height > max_height:
                        max_height = new_height
                        max_descendant = _hash

            self.main_chain_size = max_height
            self.head = self.processed[max_descendant]

    def maybe_vote_last_checkpoint(self, block):
        """Called after receiving a block.

        Implement the fork rule:
        maybe send a vote message where target is block
        if we are on the chain containing the justified checkpoint of the
        highest height, and we have never sent a vote for this height.

        Args:
            block: last block we processed
        """
        assert block.height % EPOCH_SIZE == 0, (
            "Block {} is not a checkpoint.".format(block.hash))

        # BNO: The target will be block (which is a checkpoint)
        target_block = block
        # BNO: The source will be the justified checkpoint of greatest height
        source_block = self.highest_justified_checkpoint


        # If the block is an epoch block of a higher epoch than what we've seen so far
        # This means that it's the first time we see a checkpoint at this height
        # It also means we never voted for any other checkpoint at this height (rule 1)
        if target_block.epoch > self.current_epoch:
            assert target_block.epoch > source_block.epoch, ("target epoch: {},"
            "source epoch: {}".format(target_block.epoch, source_block.epoch))

            # print('Validator %d: now in epoch %d' % (self.id, target_block.epoch))
            # Increment our epoch
            self.current_epoch = target_block.epoch

            # if the target_block is a descendent of the source_block, send
            # a vote
            if self.is_ancestor(source_block, target_block):
                # print('Validator %d: Voting %d for epoch %d with epoch source %d' %
                      # (self.id, target_block.hash, target_block.epoch,
                       # source_block.epoch))

                vote = Vote(source_block.hash,
                            target_block.hash,
                            source_block.epoch,
                            target_block.epoch,
                            self.id)
                self.network.broadcast(vote)
                assert self.processed[target_block.hash]

    def accept_vote(self, vote):
        """Called on receiving a vote message.
        """
        # print('Node %d: got a vote' % self.id, source.view, prepare.view_source,
              # prepare.blockhash, vote.blockhash in self.processed)

       # If the block has not yet been processed, wait
        if vote.source not in self.processed:
            self.add_dependency(vote.source, vote)

        # Check that the source is processed and justified
        # TODO: If the source is not justified, add to dependencies?
        if vote.source not in self.justified:
            return False

        # If the target has not yet been processed, wait
        if vote.target not in self.processed:
            self.add_dependency(vote.target, vote)
            return False

        # If the target is not a descendent of the source, ignore the vote
        if not self.is_ancestor(vote.source, vote.target):
            return False

        # If the sender is not in the block's dynasty, ignore the vote
        # TODO: is it really vote.target? (to check dynasties)
        # TODO: reorganize dynasties like the paper
        if vote.sender not in self.processed[vote.target].current_dynasty.validators and \
            vote.sender not in self.processed[vote.target].prev_dynasty.validators:
            return False

        # Initialize self.votes[vote.sender] if necessary
        if vote.sender not in self.votes:
            self.votes[vote.sender] = []

        # Check the slashing conditions
        for past_vote in self.votes[vote.sender]:
            if past_vote.epoch_target == vote.epoch_target:
                # TODO: SLASH
                print('You just got slashed.')
                return False

            if ((past_vote.epoch_source < vote.epoch_source and
                 past_vote.epoch_target > vote.epoch_target) or
               (past_vote.epoch_source > vote.epoch_source and
                 past_vote.epoch_target < vote.epoch_target)):
                print('You just got slashed.')
                return False

        # Add the vote to the map of votes
        self.votes[vote.sender].append(vote)

        # Add to the vote count
        if vote.source not in self.vote_count:
            self.vote_count[vote.source] = {}
        self.vote_count[vote.source][vote.target] = self.vote_count[
            vote.source].get(vote.target, 0) + 1

        # TODO: we do not deal with finalized dynasties (the pool of validator
        # is always the same right now)
        # If there are enough votes, process them
        if (self.vote_count[vote.source][vote.target] > (NUM_VALIDATORS * 2) // 3):
            # Mark the target as justified
            self.justified.add(vote.target)
            if vote.epoch_target > self.highest_justified_checkpoint.epoch:
                self.highest_justified_checkpoint = self.processed[vote.target]

            # If the source was a direct parent of the target, the source
            # is finalized
            if vote.epoch_source == vote.epoch_target - 1:
                self.finalized.add(vote.source)
        return True

    # Called on processing any object
    def on_receive(self, obj):
        if obj.hash in self.processed:
            return False
        if isinstance(obj, Block):
            o = self.accept_block(obj)
        elif isinstance(obj, Vote):
            o = self.accept_vote(obj)
        # If the object was successfully processed
        # (ie. not flagged as having unsatisfied dependencies)
        if o:
            self.processed[obj.hash] = obj
            if obj.hash in self.dependencies:
                for d in self.dependencies[obj.hash]:
                    self.on_receive(d)
                del self.dependencies[obj.hash]
