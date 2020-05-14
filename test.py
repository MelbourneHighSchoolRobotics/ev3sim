# This is TEMPORARY

from simulation.loader import ScriptLoader
from tests.random_testing import RandomInteractor

sl = ScriptLoader()
sl.startUp()
sl.simulate(RandomInteractor())
