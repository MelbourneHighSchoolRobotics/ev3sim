import time
from random import randint, seed as random_seed


def start_batch(batch, seed=None):
    if seed is None:
        random_seed(time.time())
        # Seed for numpy randomisation is 0 to 2^32-1, inclusive.
        seed = randint(0, (1 << 32) - 1)

    print(f"Simulating with seed {seed}")

    from ev3sim.batched_run import batched_run

    batched_run(batch, seed)
