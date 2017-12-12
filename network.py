class Network(object):
    """Networking layer controlling the delivery of messages between nodes.

    self.msg_arrivals is a table where the keys are the time of arrival of
        messages and the values is a list of the objects received at that time
    """
    def __init__(self, latency_fn):
        self.nodes = []
        self.time = 0
        self.msg_arrivals = {}
        self.latency_fn = latency_fn

    def broadcast(self, msg):
        """Broadcasts a message to all nodes in the network. (with latency)

        Inputs:
            msg: the message to be broadcastes (PREPARE or COMMIT).

        Returns:
            None
        """
        for node in self.nodes:
            # Create a different delay for every receiving node i
            # Delays need to be at least 1
            delay = self.latency_fn()
            assert delay >= 1, "delay is 0, which will lose some messages !"
            if self.time + delay not in self.msg_arrivals:
                self.msg_arrivals[self.time + delay] = []
            self.msg_arrivals[self.time + delay].append((node.id, msg))

    def tick(self):
        """Simulates a tick of time.

        Each node deals with receiving messages of time t.
        Increments the time of each node, and of the network.
        """
        if self.time in self.msg_arrivals:
            for node_index, msg in self.msg_arrivals[self.time]:
                self.nodes[node_index].on_receive(msg)
            del self.msg_arrivals[self.time]
        for n in self.nodes:
            n.tick(self.time)
        self.time += 1
