import random


def exponential_latency(avg_latency):
    """Represents the latency to transfer messages
    """
    return lambda: 1 + int(random.expovariate(1) * avg_latency)
