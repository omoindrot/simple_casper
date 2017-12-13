import random

import matplotlib.pyplot as plt
import networkx as nx
import pygraphviz  # used in the layout

from block import Block
from parameters import *


def node_checkpoints(node):
    """Get all the checkpoints of a given node, i.e. all the blocks with height % EPOCH_LENGHT == 0

    Args:
        node: Node

    Returns:
        G: networkx directed graph of the checkpoints
    """
    G = nx.DiGraph()

    # Use node.get_checkpoint_parent(block)
    for block_hash in node.processed:
        if isinstance(node.processed[block_hash], Block):
            block = node.processed[block_hash]
            # Check that the block is a checkpoint
            if block.height % EPOCH_SIZE == 0:
                G.add_node(block_hash)

                # Check if this is not the genesis block
                if block.height > 0:
                    previous_checkpoint = node.get_checkpoint_parent(block)
                    previous_checkpoint_hash = previous_checkpoint.hash

                    G.add_edge(block_hash, previous_checkpoint_hash)

    # Check that G is a tree
    assert G.number_of_nodes() == G.number_of_edges() + 1
    return G


def plot_node_blockchains(nodes, image_file):
    """Plot each node's blockchain in a subplot
    """
    num_nodes = len(nodes)

    graphs = []
    for node in nodes:
        graphs.append(node_checkpoints(node))

    #sqrt = int(num_nodes ** 0.5) + 1
    nrows = 1
    ncols = num_nodes

    plt.figure(figsize=(40, 20))
    for i in range(num_nodes):
        node = nodes[i]
        G = graphs[i]

        # Create list of committable nodes
        colors = []
        pos = {}
        labels = {}
        for block_hash in list(G.nodes()):
            block = node.processed[block_hash]
            # FOR PREPARE-COMMIT
            # if block_hash in node.committable:
            # FOR VOTE
            if node.is_finalized(block_hash):
                color = 'r'
            # TODO: add color for PREPARED checkpoints
            else:
                color = 'b'
            colors.append(color)

            height = block.height // EPOCH_SIZE
            pos[block_hash] = (random.gauss(0, 1), height)

        ax = plt.subplot(nrows, ncols, i + 1)
        ax.set_title("Node %d" % node.id)

        pos = nx.drawing.nx_agraph.pygraphviz_layout(G, prog='dot')
        nx.draw(G, arrows=True, pos=pos, node_color=colors, labels=labels)

    plt.savefig(image_file)
    plt.close()
