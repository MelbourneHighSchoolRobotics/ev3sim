from tests.interactors.spawner import SpawnerInteractor
from objects.colliders import Collider
import yaml

#I tried parsing the file so that whenever the coordinates are changed in the YAML.
"""
with open("soccer.yaml", 'r') as stream:
    try:
        print(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc, end='\n')
"""

class SoccerInteractor(SpawnerInteractor):

    def checkLeftGoal(self, other: Collider):
        if Collider.position[0] <= -940:
            #Not sure what we'll have here, but just used this for debugging purposes
            print("Goal")
        pass

    def checkRightGoal(self, other: Collider):
        if Collider.position[0] >= 940:
            print("Goal")
        pass
