from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from objects.base import objectFactory
from visual.manager import ScreenObjectManager

class SoccerInteractor(IInteractor):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.names = kwargs.get('names', ['Team 1', 'Team 2'])
        self.spawns = kwargs.get('spawns')
        self.goals = kwargs.get('goals')
    
    def startUp(self):
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(self.goals), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.team_scores = []
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
            ScreenObjectManager.instance.registerVisual(self.goal_colliders[-1].visual, f'Soccer_DEBUG_collider-{len(self.goal_colliders)}')
            # Set up team scores
            self.team_scores.append(0)
            # Set up team name
            ScriptLoader.instance.object_map[f'name{x+1}Text'].text = self.names[x]
        self.updateScoreText()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f'score{x+1}Text'].text = str(self.team_scores[x])

    def tick(self, tick):
        super().tick(tick)
        # TODO: Check ball for collisions with goal objects.
        # TODO: If so, reset game, change team score value.
