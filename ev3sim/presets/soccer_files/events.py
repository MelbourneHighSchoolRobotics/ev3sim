import pymunk
import pygame

from ev3sim.presets.soccer_files.game_logic import SoccerLogicInteractor
from ev3sim.presets.soccer_files.ui import SoccerUIInteractor
from ev3sim.objects.base import STATIC_CATEGORY
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World
from ev3sim.visual.utils import screenspace_to_worldspace


class SoccerEventsInteractor(IInteractor):

    # Must occur before device interactors.
    SORT_ORDER = -11
    instance = None

    def __init__(self, **kwargs):
        SoccerEventsInteractor.instance = self
        super().__init__(**kwargs)

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
            for shape in shapes:
                for team in range(len(SoccerUIInteractor.instance.names)):
                    # Goal change functionality
                    if shape.shape.obj.key.startswith(f"score{team+1}"):
                        action = shape.shape.obj.key.split(str(team + 1))[1]
                        if action == "Plus":
                            SoccerLogicInteractor.instance.team_scores[team] += 1
                        elif action == "Minus":
                            if SoccerLogicInteractor.instance.team_scores[team] > 0:
                                SoccerLogicInteractor.instance.team_scores[team] -= 1
                        else:
                            raise ValueError(f"Unhandled team action {action}")
                        SoccerUIInteractor.instance.updateScoreText(SoccerLogicInteractor.instance.team_scores)
                    # Early penalty end
                    for index in range(SoccerLogicInteractor.instance.BOTS_PER_TEAM):
                        actual_index = team + index * len(SoccerUIInteractor.instance.names)
                        if actual_index < len(self.robots):
                            if shape.shape.obj.key == f"UI-penalty-{actual_index}":
                                SoccerLogicInteractor.instance.finishPenalty(actual_index)
                if shape.shape.obj.key == "controlsReset":
                    SoccerUIInteractor.instance.onResetPressed()

        if event.type == pygame.MOUSEMOTION:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
            # Penalty UI hover colour.
            for team in range(len(SoccerUIInteractor.instance.names)):
                for index in range(SoccerLogicInteractor.instance.BOTS_PER_TEAM):
                    actual_index = team + index * len(SoccerUIInteractor.instance.names)
                    for shape in shapes:
                        if shape.shape.obj.key == f"UI-penalty-{team + index * len(SoccerUIInteractor.instance.names)}":
                            shape.shape.obj.visual.fill = "penalty_ui_bg_hover"
                            break
                    else:
                        key = f"UI-penalty-{team + index * len(SoccerUIInteractor.instance.names)}"
                        if key in ScriptLoader.instance.object_map:
                            ScriptLoader.instance.object_map[key].visual.fill = "penalty_ui_bg"

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            shapes = World.instance.space.point_query(
                [float(v) for v in m_pos], 0.0, pymunk.ShapeFilter(mask=STATIC_CATEGORY)
            )
            reset_hovered = False
            for shape in shapes:
                if shape.shape.obj.key == "controlsReset":
                    reset_hovered = True
            SoccerUIInteractor.instance.onResetReleased(reset_hovered)
