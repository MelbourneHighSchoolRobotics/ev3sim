import numpy as np
from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from objects.base import objectFactory
from visual.manager import ScreenObjectManager

class SoccerInteractor(IInteractor):
    
    BOTS_PER_TEAM = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.names = kwargs.get('names', ['Team 1', 'Team 2'])
        self.spawns = kwargs.get('spawns')
        self.goals = kwargs.get('goals')
        self.show_goal_colliders = kwargs.get('show_goal_colliders', False)
    
    def startUp(self):
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(self.goals), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.team_scores = []
        self.robots = []
        for x in range(len(self.names)):
            # Set up goal collider.
            pos = self.goals[x]['position']
            del self.goals[x]['position']
            obj = {
                'collider': 'inherit',
                'visual': self.goals[x],
                'position': pos
            }
            self.goal_colliders.append(objectFactory(**obj))
            if self.show_goal_colliders:
                ScreenObjectManager.instance.registerVisual(self.goal_colliders[-1].visual, f'Soccer_DEBUG_collider-{len(self.goal_colliders)}')
            # Set up team scores
            self.team_scores.append(0)
            # Set up team name
            ScriptLoader.instance.object_map[f'name{x+1}Text'].text = self.names[x]
            for y in range(self.BOTS_PER_TEAM):
                # Find the BOTS_PER_TEAM*x+yth robot.
                possible_keys = []
                for key in ScriptLoader.instance.object_map.keys():
                    if key.startswith(f'Robot-{self.BOTS_PER_TEAM*x+y}'):
                        possible_keys.append(key)
                if len(possible_keys) == 0:
                    raise ValueError(f"No Robot-{self.BOTS_PER_TEAM*x+y} for simulation, quitting.")
                possible_keys.sort(key=len)
            self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
        self.updateScoreText()
        self.resetPositions()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f'score{x+1}Text'].text = str(self.team_scores[x])

    def resetPositions(self):
        # It is assumed that 2 robots to each team, with indexes increasing as we go across teams.
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                self.robots[team*self.BOTS_PER_TEAM + index].position = self.spawns[team][index][0]
                self.robots[team*self.BOTS_PER_TEAM + index].rotation = self.spawns[team][index][1] * np.pi / 180
        ScriptLoader.instance.object_map['IR_BALL'].position = [0, -18]

    def tick(self, tick):
        super().tick(tick)
        # TODO: Check ball for collisions with goal objects.
        # TODO: If so, reset game, change team score value.
