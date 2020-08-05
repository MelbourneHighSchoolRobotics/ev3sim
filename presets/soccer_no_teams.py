import numpy as np
from objects.base import objectFactory
from presets.soccer import SoccerInteractor as BaseInteractor
from simulation.loader import ScriptLoader
from simulation.world import World
from visual.manager import ScreenObjectManager

class SoccerInteractor(BaseInteractor):

    def startUp(self):
        self.goal_colliders = []
        self.locateBots()

        self.ball_centre = objectFactory(**{
            'collider': 'inherit',
            'visual': {
                'name': 'Circle',
                'radius': 0.1
            },
            'physics': True
        })
        self.ball_centre.shape.sensor = True
        self.ball_centre.shape.collision_type = self.BALL_COLLISION_TYPE
        World.instance.registerObject(self.ball_centre)

        for x in range(len(self.goals)):
            pos = self.goals[x]['position']
            del self.goals[x]['position']
            obj = {
                'collider': 'inherit',
                'visual': self.goals[x],
                'position': pos,
                'physics': True
            }
            self.goal_colliders.append(objectFactory(**obj))
            if self.show_goal_colliders:
                ScreenObjectManager.instance.registerVisual(self.goal_colliders[-1].visual, f'Soccer_DEBUG_collider-{len(self.goal_colliders)}')
        self.resetPositions()
        for robot in self.robots:
            robot.robot_class.onSpawn()
    
    def resetPositions(self):
        for x in range(len(self.robots)):
            self.robots[x].body.position = self.spawns[x][0]
            self.robots[x].body.angle = self.spawns[x][1] * np.pi / 180
            self.robots[x].body.velocity = np.array([0., 0.])
        ScriptLoader.instance.object_map['IR_BALL'].body.position = [0, -18]
        ScriptLoader.instance.object_map['IR_BALL'].body.velocity = np.array([0., 0.])

    def goalScoredIn(self, teamIndex, tick):
        self.resetPositions()
        # Pause the game temporarily
        World.instance.paused = True
        self.current_goal_score_tick = tick