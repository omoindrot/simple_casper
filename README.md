# A simple implementation of Casper
Authors: Charles Bournhonesque, Olivier Moindrot

Project realized for the class CS244b at Stanford.  
Final report for the class: [final_report.pdf](final_report.pdf)


Original paper Casper from Vitalik Buterin and Virgil Griffith.  
- Paper: https://arxiv.org/abs/1710.09437  
- Original code: https://github.com/ethereum/casper


### Running the code

The parameters of the experiment can be found in `parameters.py`.

To reproduce figure 1 in our report, use the following parameters and run `python3 simulator.py`.

```python
NUM_VALIDATORS = 3  # number of validators at each checkpoint
VALIDATOR_IDS = list(range(0, NUM_VALIDATORS))  # set of validators
INITIAL_VALIDATORS = list(range(0, NUM_VALIDATORS))  # set of validators for root
BLOCK_PROPOSAL_TIME = 100  # adds a block every 100 ticks
EPOCH_SIZE = 5  # checkpoint every 5 blocks
AVG_LATENCY = 100  # average latency of the network (in number of ticks)
```


To reproduce figures 2 and 3, use the following parameters and run `python3 metrics.py`.

```python
NUM_VALIDATORS = 100  # number of validators at each checkpoint
VALIDATOR_IDS = list(range(0, NUM_VALIDATORS))  # set of validators
INITIAL_VALIDATORS = list(range(0, NUM_VALIDATORS))  # set of validators for root
BLOCK_PROPOSAL_TIME = 100  # adds a block every 100 ticks
EPOCH_SIZE = 5  # checkpoint every 5 blocks
AVG_LATENCY = 100  # will be modified in metrics
```
