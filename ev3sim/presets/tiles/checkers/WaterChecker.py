from ev3sim.presets.tiles.checkers.CompletedChecker import CompletedChecker
from ev3sim.simulation.world import stop_on_pause
from ev3sim.objects.utils import magnitude_sq


class WaterChecker(CompletedChecker):

    COMPLETE_SCORE = 20
    MAX_WATER_VELOCITY_SQ = 100

    def onReset(self):
        super().onReset()
        self.waterTower.body.position = [float(v) for v in self.rescue.tiles[self.index]["all_elems"][0].position]

    @property
    def waterTower(self):
        return self.rescue.tiles[self.index]["all_elems"][3]

    @stop_on_pause
    def tick(self, tick):
        # Make sure the water tower is in the tile, and has small velocity
        if magnitude_sq(self.waterTower.body.velocity) > self.MAX_WATER_VELOCITY_SQ:
            # Bad! Infer which bot based on in the tile.
            self.rescue.lackOfProgress(0)
            return
        pos1 = self.waterTower.position
        pos2 = self.rescue.tiles[self.index]["all_elems"][0].position
        if abs(pos1[0] - pos2[0]) > self.rescue.TILE_LENGTH / 2 or abs(pos1[1] - pos2[1]) > self.rescue.TILE_LENGTH / 2:
            # Bad! Infer which bot based on in the tile.
            self.rescue.lackOfProgress(0)
