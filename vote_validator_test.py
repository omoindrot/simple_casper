"""Test the values of a validator to make sure we don't violate any condition.

Conditions to respect:
    (1) a validator cannot vote on two different target checkpoints at same height
    (2) a validator cannot vote (c_1 -> c_4) and (c_2 -> c_3) if c_1 < c_2 < c_3 < c_4 (sandwich)
"""


def test_rule_1(validator):
    """Check rule 1: a validator cannot vote on two different target checkpoints at the same height
    """
    votes = validator.votes[validator.id]  # dict {sender_id: votes}

    # Dict mapping height to votes targeting this height
    height_to_vote = {}
    for vote in votes:
        assert vote.sender == validator.id,\
               "senders don't match: %d and %d" % (vote.sender, validator.id)

        if vote.epoch_target not in height_to_vote:
            height_to_vote[vote.epoch_target] = []

        height_to_vote[vote.epoch_target].append(vote)

    # Check that we have at most one vote at each height
    for height in height_to_vote:
        assert len(height_to_vote[height]) <= 1


def test_rule_2(validator):
    """Check rule 2: sandwich rule

    A validator cannot vote on (c_1 -> c_4) and (c_2 -> c_3) if c_1 < c_2 < c_3 < c_4
    """
    votes = validator.votes[validator.id]  # dict {sender_id: votes}

    # Dict mapping height to votes targeting this height
    height_to_vote = {}
    for vote in votes:
        assert vote.sender == validator.id,\
               "senders don't match: %d and %d" % (vote.sender, validator.id)

        if vote.epoch_target not in height_to_vote:
            height_to_vote[vote.epoch_target] = []

        height_to_vote[vote.epoch_target].append(vote)

    heights = height_to_vote.keys()
    heights.sort()

    for height in heights:
        c4 = height
        # Check for votes (c_1 -> c_4) if there are votes (c_2 -> c_3)
        assert len(height_to_vote[c4]) <= 1  # rule 1
        vote = height_to_vote[c4]

        c1 = vote.epoch_source
        for c3 in heights:
            if c1 < c3 and c3 < c4:
                vote_bis = height_to_vote[c3]
                c2 = vote_bis.epoch_source
                assert c2 <= c1, "Rule 2 is broken ! %d, %d, %d, %d" % (c1, c2, c3, c4)


def is_finalized(validator, hash_):
    """Returns true if the `hash_` corresponds to a finalized block for validator.

    A checkpoint c in finalized if it is justified and there exist a supermajority link
    (c -> c') where c' is a direct checkpoint child of c.
    """
    assert hash_ in validator.processed, "Couldn't find block hash %d" % hash_
    source = validator.processed[hash_]
    assert source.height % EPOCH_LENGTH == 0, "Block is not a checkpoint"

    # Check that the checkpoint is justified
    if not validator.is_justified(hash_):
        return False

    # If there is not votes with hash_ as source
    if hash_ not in validator.vote_count:
        return False

    # Find a direct checkpoint child of c, with a supermajority link (c -> c')
    for target_hash in validator.vote_count[hash_]:
        target = validator.processed[target_hash]
        assert target.height % EPOCH_LENGTH == 0, "Block is not a checkpoint"

        vote_count = validator.vote_count[hash_][target_hash]

        if (source.height == target.height - EPOCH_SIZE and
            vote_count > (NUM_VALIDATORS * 2) // 3):
            return True

    return False
