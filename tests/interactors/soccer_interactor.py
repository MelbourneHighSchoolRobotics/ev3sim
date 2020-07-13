from tests.interactors.spawner import SpawnerInteractor
from objects.colliders import Collider
import yaml

# Uncomment to parse the file so that whenever the coordinates are changed in the YAML
# we can store the x-coordinate of the goal line in a variable
"""
with open("soccer.yaml", 'r') as stream:
    try:
        print(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc, end='\n')
"""

class SoccerInteractor(SpawnerInteractor):
    # Define team1 as going from left to right, and team2 as going from right to left
    team1_score = 0
    team2_score = 0

    def checkLeftGoal(self, other: Collider):
        if other.position[0] <= -940:
            # Not sure what we'll have here, but just used this for debugging purposes
            print("Goal")
            self.team2_score += 1
        pass

    def checkRightGoal(self, other: Collider):
        if other.position[0] >= 940:
            print("Goal")
            self.team1_score += 1
        pass

    def getScore(self, team):
        return self.team1_score if team == 'team1' else self.team2_score

    def tick(self, tick):
        return self.object_map['team_score'].get(team='')

