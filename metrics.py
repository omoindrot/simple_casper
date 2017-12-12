import os
import numpy as np

from parameters import *
from block import Block
from utils import exponential_latency
from network import Network
from validator import VoteValidator
from plot_graph import plot_node_blockchains


def fraction_justified_and_finalized(validator):
    """Compute the fraction of justified and finalized checkpoints in the main chain.

    From the genesis block to the highest justified checkpoint, count the fraction of checkpoints
    in each state.
    """
    # Get the main chain
    checkpoint = validator.highest_justified_checkpoint

    count_justified = 0
    count_finalized = 0
    count_total = 0
    while checkpoint is not None:
        count_total += 1
        if checkpoint.hash in validator.justified:
            count_justified += 1
        if checkpoint.hash in validator.finalized:
            count_finalized += 1
        checkpoint = validator.get_checkpoint_parent(checkpoint)

    fraction_justified = float(count_justified) / float(count_total)
    fraction_finalized = float(count_finalized) / float(count_total)
    count_forked_justified = len(validator.justified) - count_justified
    fraction_forked_justified = float(count_forked_justified) / float(count_total)
    return fraction_justified, fraction_finalized, fraction_forked_justified


def main_chain_size(validator):
    """Computes the number of blocks in the main chain."""
    return validator.highest_justified_checkpoint.height + 1


def blocks_under_highest_justified(validator):
    """Computes the height of blocks below the checkpoint of highest height."""
    res = 0
    for bhash, b in validator.processed.items():
        if isinstance(b, Block):
            if b.height <= validator.highest_justified_checkpoint.height:
                res += 1
    return res


def total_height_blocks(validator):
    """Total height of blocks processed by the validator.
    """
    res = 0
    for bhash, b in validator.processed.items():
        if isinstance(b, Block):
            res += 1
    return res


def count_forks(validator):
    """Compute the height of forks of each size.

    Returns a dict {1: 24, 2: 5, 3: 2} for instance.
    Compute forks up until the highest justified checkpoint.
    """
    # Compute a list of the block hashes in the main chain, up to the highest justified checkpoint.
    block = validator.highest_justified_checkpoint
    block_hash = block.hash
    main_blocks = [block_hash]

    # Stop when we reach the genesis block
    while block.height > 0:
        block_hash = block.prevhash
        block = validator.processed[block_hash]
        main_blocks.append(block_hash)

    # Check that we reached the genesis block
    assert block.height == 0
    assert len(main_blocks) == validator.highest_justified_checkpoint.height + 1

    # Now iterate through the blocks with height below highest_justified
    longest_fork = {}
    for block_hash, block in validator.processed.items():
        if isinstance(block, Block):
            if block.height <= validator.highest_justified_checkpoint.height:
                # Get the closest parent of block from the main blockchain
                fork_length = 0
                while block_hash not in main_blocks:
                    fork_length += 1
                    block_hash = block.prevhash
                    block = validator.processed[block_hash]
                assert block_hash in main_blocks
                longest_fork[block_hash] = max(longest_fork.get(block_hash, 0), fork_length)

    count_forks = {}
    for block_hash in main_blocks:
        l = longest_fork[block_hash]
        count_forks[l] = count_forks.get(l, 0) + 1

    assert sum(count_forks.values()) == validator.highest_justified_checkpoint.height + 1
    return count_forks


def print_metrics_latency(latencies, num_tries, validator_set=VALIDATOR_IDS):
    for latency in latencies:
        jfsum = 0.0
        ffsum = 0.0
        jffsum = 0.0
        mcsum = 0.0
        busum = 0.0
        #fcsum = {}
        for i in range(num_tries):
            network = Network(exponential_latency(latency))
            validators = [VoteValidator(network, i) for i in validator_set]

            for t in range(BLOCK_PROPOSAL_TIME * EPOCH_SIZE * 50):
                network.tick()
                # if t % (BLOCK_PROPOSAL_TIME * EPOCH_SIZE) == 0:
                #     filename = os.path.join(LOG_DIR, 'plot_{:03d}.png'.format(t))
                #     plot_node_blockchains(validators, filename)

            for val in validators:
                jf, ff, jff = fraction_justified_and_finalized(val)
                jfsum += jf
                ffsum += ff
                jffsum += jff
                mcsum += main_chain_size(val)
                busum += blocks_under_highest_justified(val)
                #fc = count_forks(val)
                #for l in fc.keys():
                    #fcsum[l] = fcsum.get(l, 0) + fc[l]

        print('Latency: {}'.format(latency))
        print('Justified: {}'.format(jfsum / len(validators) / num_tries))
        print('Finalized: {}'.format(ffsum / len(validators) / num_tries))
        print('Justified in forks: {}'.format(jffsum / len(validators) / num_tries))
        print('Main chain size: {}'.format(mcsum / len(validators) / num_tries))
        print('Blocks under main justified: {}'.format(busum / len(validators) / num_tries))
        print('Main chain fraction: {}'.format(
            mcsum / (len(validators) * num_tries * (EPOCH_SIZE * 50 + 1))))
        #for l in sorted(fcsum.keys()):
            #if l > 0:
                #frac = float(fcsum[l]) / float(fcsum[0])
                #print('Fraction of forks of size {}: {}'.format(l, frac))
        print('')


if __name__ == '__main__':
    LOG_DIR = 'metrics'
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Uncomment to have fractions of disconnected nodes
    # fractions = np.arange(0.0, 0.4, 0.05)
    # fractions = [0.31, 0.32, 0.33]
    fractions = [0.0]
    for fraction_disconnected in fractions:
        num_validators = int((1.0 - fraction_disconnected) * NUM_VALIDATORS)
        validator_set = VALIDATOR_IDS[:num_validators]

        print("Total height of nodes: {}".format(NUM_VALIDATORS))
        print("height of connected of nodes: {}".format(len(validator_set)))

        # Uncomment to have different latencies
        #latencies = [i for i in range(10, 300, 20)] + [500, 750, 1000]
        latencies = [100]
        num_tries = 10  # number of samples for each set of parameters

        print_metrics_latency(latencies, num_tries, validator_set)
