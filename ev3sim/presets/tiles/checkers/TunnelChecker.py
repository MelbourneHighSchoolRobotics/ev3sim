from ev3sim.presets.tiles.checkers.CompletedChecker import CompletedChecker
from ev3sim.simulation.world import stop_on_pause
from ev3sim.objects.utils import magnitude_sq, local_space_to_world_space


class TunnelChecker(CompletedChecker):

    COMPLETE_SCORE = 20
    MAX_TUNNEL_VELOCITY_SQ = 100

    def onReset(self):
        super().onReset()
        self.tunnelTop.body.position = [
            float(v)
            for v in local_space_to_world_space(
                [0, 9],
                self.rescue.tiles[self.index]["rotation"],
                self.rescue.tiles[self.index]["all_elems"][0].position,
            )
        ]
        self.tunnelBot.body.position = [
            float(v)
            for v in local_space_to_world_space(
                [0, -9],
                self.rescue.tiles[self.index]["rotation"],
                self.rescue.tiles[self.index]["all_elems"][0].position,
            )
        ]

    @property
    def tunnelTop(self):
        return self.rescue.tiles[self.index]["all_elems"][2]

    @property
    def tunnelBot(self):
        return self.rescue.tiles[self.index]["all_elems"][3]

    @stop_on_pause
    def tick(self, tick):
        # Make sure the water tower is in the tile, and has small velocity
        if (
            magnitude_sq(self.tunnelTop.body.velocity) > self.MAX_TUNNEL_VELOCITY_SQ
            or magnitude_sq(self.tunnelBot.body.velocity) > self.MAX_TUNNEL_VELOCITY_SQ
        ):
            # Bad! Infer which bot based on in the tile.
            self.rescue.lackOfProgress(0)
            return

        pos1 = self.tunnelTop.position
        pos2 = self.rescue.tiles[self.index]["all_elems"][0].position
        if abs(pos1[0] - pos2[0]) > self.rescue.TILE_LENGTH / 2 or abs(pos1[1] - pos2[1]) > self.rescue.TILE_LENGTH / 2:
            # Bad! Infer which bot based on in the tile.
            self.rescue.lackOfProgress(0)

        pos1 = self.tunnelBot.position
        pos2 = self.rescue.tiles[self.index]["all_elems"][0].position
        if abs(pos1[0] - pos2[0]) > self.rescue.TILE_LENGTH / 2 or abs(pos1[1] - pos2[1]) > self.rescue.TILE_LENGTH / 2:
            # Bad! Infer which bot based on in the tile.
            self.rescue.lackOfProgress(0)
