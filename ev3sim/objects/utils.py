import numpy as np


def local_space_to_world_space(vector, world_rotation, world_pos):
    if len(world_pos) > 2:
        world_pos = world_pos[:2]
    return (
        np.array(
            [
                vector[0] * np.cos(world_rotation) - vector[1] * np.sin(world_rotation),
                vector[1] * np.cos(world_rotation) + vector[0] * np.sin(world_rotation),
            ]
        )
        + world_pos[:2]
    )


def magnitude_sq(vector):
    return sum(pow(a, 2) for a in vector)
