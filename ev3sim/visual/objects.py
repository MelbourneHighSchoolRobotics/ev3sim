import numpy as np
import pygame
import pygame.freetype
import pymunk
from typing import Optional, Tuple

from ev3sim.visual.manager import ScreenObjectManager
import ev3sim.visual.utils as utils
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.search_locations import asset_locations

USE_PYGAME_GFX = True


class IVisualElement:
    """
    A visual element defines some object which can be drawn to the screen, but also can generate a physics object if necessary.
    """

    _position: np.ndarray
    _rotation: float
    zPos: float
    """The z Position of the element (higher values for z will be drawn on top of other elements with lower z values)"""
    sensorVisible: bool
    """Specifies whether the visual object should affect the colour sensor readings."""

    customMap = None

    def __init__(self, **kwargs):
        self.initFromKwargs(**kwargs)

    def initFromKwargs(self, **kwargs):
        """Initialise the visual object given some extra named arguments (normally provided in the ``.yaml`` files)."""
        self.position = kwargs.get("position", [0, 0])
        self.rotation = kwargs.get("rotation", 0)
        self.zPos = kwargs.get("zPos", 0)
        self.sensorVisible = kwargs.get("sensorVisible", False)
        self.visible = kwargs.get("visible", True)

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.position = (
            pos[0] + amount * (self.position[0] - pos[0]),
            pos[1] + amount * (self.position[1] - pos[1]),
        )

    @property
    def position(self) -> np.ndarray:
        """
        The global position of the visual object - **Do not** set this when specifying local position of an object! Set the parent object position!

        :math:`0,0` is the default as centre of the screen, x increasing to the right and y increasing upwards.
        By convention, please let this position be the **centre** of your object.
        """
        return self._position

    @property
    def rotation(self) -> float:
        """
        Rotation of a visual element is float, which should in theory range from :math:`0` to :math:`2\pi`, but should still work outside of those bounds.
        """
        return self._rotation

    @position.setter
    def position(self, value):
        if not isinstance(value, np.ndarray):
            self._position = np.array(value)
        else:
            self._position = value
        try:
            # Don't worry if some stuff isn't ready yet.
            self.calculatePoints()
        except AttributeError:
            pass

    @rotation.setter
    def rotation(self, value):
        self._rotation = value
        try:
            # Don't worry if some stuff isn't ready yet.
            self.calculatePoints()
        except AttributeError:
            pass

    def applyToScreen(self, screen):
        """
        A method that all visual elements must implement.
        When invoked, should apply themselves to the screen.
        """
        raise NotImplementedError(
            f"The VisualElement {self.__cls__} does not implement the pivotal method `applyToScreen`"
        )

    def calculatePoints(self):
        """
        Called whenever the position or rotation of the object is changed, allowing for any calculation needed to be made.
        """
        raise NotImplementedError(
            f"The VisualElement {self.__cls__} does not implement the pivotal method `calculatePoints`"
        )

    def generateBodyAndShape(self, physObj, body=None, rel_pos=None):
        """
        Generates the physics object for this particular visual element. See other implementations of this method for examples.

        :param ev3sim.objects.base.PhysicsObject physObj: The physics object requesting this body and shape.
        :param pymunk.Body body: If you don't want a new body generated, supply one.
        :param tuple rel_pos: If an existing body was specified, then this is the relative position of the shape on the body.
        :returns (pymunk.Body, pymunk.Shape): The generated objects.
        """
        raise NotImplementedError(
            f"The VisualElement {self.__cls__} does not implement the pivotal method `generateShape`"
        )

    def getPositionAnchorOffset(self):
        return np.array([0.0, 0.0])


class Colorable(IVisualElement):
    _fill: Optional[Tuple[int]]
    _stroke: Optional[Tuple[int]]
    stroke_width: float

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.fill = kwargs.get("fill", "#ffffff")
        self.stroke = kwargs.get("stroke", None)
        self.stroke_width = kwargs.get("stroke_width", 1)

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.stroke_width *= amount
        super().scaleAtPosition(amount, pos=pos)

    @property
    def fill(self) -> Tuple[int]:
        return self._fill

    @fill.setter
    def fill(self, value):
        if isinstance(value, str):
            if value in utils.GLOBAL_COLOURS:
                value = utils.GLOBAL_COLOURS[value]
            if value.startswith("#"):
                value = value[1:]
            self._fill = utils.hex_to_pycolor(value)
        else:
            self._fill = value

    @property
    def stroke(self) -> Tuple[int]:
        return self._stroke

    @stroke.setter
    def stroke(self, value):
        if isinstance(value, str):
            if value in utils.GLOBAL_COLOURS:
                value = utils.GLOBAL_COLOURS[value]
            if value.startswith("#"):
                value = value[1:]
            self._stroke = utils.hex_to_pycolor(value)
        else:
            self._stroke = value

    @property
    def scaledStrokeWidth(self):
        if self.customMap is None:
            return max(
                1,
                int(
                    self.stroke_width
                    * ScreenObjectManager.instance.SCREEN_WIDTH
                    / ScreenObjectManager.instance.MAP_WIDTH
                ),
            )
        return max(
            1,
            int(self.stroke_width * self.customMap["SCREEN_WIDTH"] / self.customMap["MAP_WIDTH"]),
        )


class Image(Colorable):
    def initFromKwargs(self, **kwargs):
        self._image_path = ""
        super().initFromKwargs(**kwargs)
        self.fill = kwargs.get("fill", (0, 0, 0, 0))
        self.hAlignment = kwargs.get("hAlignment", "m")
        self.vAlignment = kwargs.get("vAlignment", "m")
        self.scale = kwargs.get("scale", 1)
        self.flip = kwargs.get("flip", [False, False])
        self.image_path = kwargs.get("image_path")
        self.calculatePoints()

    def scaleAtPosition(self, amount, pos=(0, 0)):
        if isinstance(self.scale, (tuple, list)):
            if isinstance(amount, (tuple, list)):
                self.scale = (self.scale[0] * amount[0], self.scale[1] * amount[1])
            else:
                self.scale = (self.scale[0] * amount, self.scale[1] * amount)
        else:
            if isinstance(amount, (tuple, list)):
                self.scale = (self.scale * amount[0], self.scale * amount[1])
            else:
                self.scale *= amount
        super().scaleAtPosition(amount, pos=pos)

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        from ev3sim.file_helper import find_abs

        image_path = find_abs(value, allowed_areas=asset_locations())
        if image_path != self._image_path:
            self._image_path = image_path
            self.image = pygame.image.load(self._image_path)
            try:
                self.calculatePoints()
            except:
                pass

    def calculatePoints(self):
        if self.customMap is None:
            relative_scale = ScreenObjectManager.instance.relativeScreenScale()
            # In order to have a reasonably sized image at all resolutions, calculate the scale to use based on the starting screen scale as well.
            relative_scale = relative_scale * ScreenObjectManager.instance.original_SCREEN_WIDTH / 1280
        else:
            relative_scale = self.customMap["SCREEN_WIDTH"] / 1280 * 293.3 / self.customMap["MAP_WIDTH"]
        new_size = [
            int(
                self.image.get_size()[0]
                * (self.scale[0] if isinstance(self.scale, (list, tuple)) else self.scale)
                * relative_scale
            ),
            int(
                self.image.get_size()[1]
                * (self.scale[1] if isinstance(self.scale, (list, tuple)) else self.scale)
                * relative_scale
            ),
        ]
        scaled = pygame.transform.scale(self.image, new_size)
        flipped = pygame.transform.flip(scaled, self.flip[0], self.flip[1])
        self.rotated = pygame.transform.rotate(flipped, self.rotation * 180 / np.pi)
        self.rotated.fill(self.fill, special_flags=pygame.BLEND_ADD)
        self.screen_location = utils.worldspace_to_screenspace(self.position, self.customMap)
        self.screen_size = self.rotated.get_size()
        if self.hAlignment == "l":
            pass
        elif self.hAlignment == "m":
            self.screen_location -= np.array([self.screen_size[0] / 2, 0.0])
        elif self.hAlignment == "r":
            self.screen_location -= np.array([self.screen_size[0], 0.0])
        else:
            raise ValueError(f"hAlignment is incorrect: {self.hAlignment}")
        if self.vAlignment == "t":
            pass
        elif self.vAlignment == "m":
            self.screen_location -= np.array([0.0, self.screen_size[1] / 2])
        elif self.vAlignment == "b":
            self.screen_location -= np.array([0.0, self.screen_size[1]])
        else:
            raise ValueError(f"vAlignment is incorrect: {self.vAlignment}")
        from ev3sim.visual.utils import screenspace_to_worldspace

        if self.customMap is None:
            physics_size = screenspace_to_worldspace(
                [
                    ScreenObjectManager.instance._SCREEN_WIDTH_ACTUAL / 2 + self.screen_size[0],
                    ScreenObjectManager.instance._SCREEN_HEIGHT_ACTUAL / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        else:
            physics_size = screenspace_to_worldspace(
                [
                    self.customMap["SCREEN_WIDTH"] / 2 + self.screen_size[0],
                    self.customMap["SCREEN_HEIGHT"] / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        self.verts = [
            (physics_size[0] / 2, physics_size[1] / 2),
            (physics_size[0] / 2, -physics_size[1] / 2),
            (-physics_size[0] / 2, -physics_size[1] / 2),
            (-physics_size[0] / 2, physics_size[1] / 2),
        ]

    def applyToScreen(self, screen):
        screen.blit(self.rotated, self.screen_location)

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_poly(physObj.mass, self.verts)
            body = pymunk.Body(
                physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC
            )
        shape = pymunk.Poly(
            body,
            self.verts,
            transform=pymunk.Transform(
                a=np.cos(physObj.rotation),
                b=np.sin(physObj.rotation),
                c=-np.sin(physObj.rotation),
                d=np.cos(physObj.rotation),
                tx=rel_pos[0],
                ty=rel_pos[1],
            ),
        )
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        shape.sensor = physObj.sensor
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY

        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape

    def getPositionAnchorOffset(self):
        res = np.array([0.0, 0.0])
        from ev3sim.visual.utils import screenspace_to_worldspace

        if self.customMap is None:
            physics_size = screenspace_to_worldspace(
                [
                    ScreenObjectManager.instance._SCREEN_WIDTH_ACTUAL / 2 + self.screen_size[0],
                    ScreenObjectManager.instance._SCREEN_HEIGHT_ACTUAL / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        else:
            physics_size = screenspace_to_worldspace(
                [
                    self.customMap["SCREEN_WIDTH"] / 2 + self.screen_size[0],
                    self.customMap["SCREEN_HEIGHT"] / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        if self.hAlignment == "l":
            res += np.array([physics_size[0] / 2, 0.0])
        elif self.hAlignment == "m":
            pass
        elif self.hAlignment == "r":
            res -= np.array([physics_size[0] / 2, 0.0])
        else:
            raise ValueError(f"hAlignment is incorrect: {self.hAlignment}")
        if self.vAlignment == "t":
            res += np.array([0.0, physics_size[1] / 2])
        elif self.vAlignment == "m":
            pass
        elif self.vAlignment == "b":
            res -= np.array([0.0, physics_size[1] / 2])
        else:
            raise ValueError(f"vAlignment is incorrect: {self.vAlignment}")
        return res


class Line(Colorable):
    # THESE DON'T HAVE A LOCAL POSITION

    def initFromKwargs(self, **kwargs):
        self.start = kwargs.get("start")
        self.end = kwargs.get("end")
        super().initFromKwargs(**kwargs)

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.start = (
            pos[0] + amount * (self.start[0] - pos[0]),
            pos[1] + amount * (self.start[1] - pos[1]),
        )
        self.end = (
            pos[0] + amount * (self.end[0] - pos[0]),
            pos[1] + amount * (self.end[1] - pos[1]),
        )
        super().scaleAtPosition(amount, pos=pos)

    def calculatePoints(self):
        return

    def _applyToScreen(self, screen):
        if self.stroke and self.stroke_width:
            pygame.draw.line(
                screen,
                self.fill,
                utils.worldspace_to_screenspace(self.start, self.customMap),
                utils.worldspace_to_screenspace(self.end, self.customMap),
                self.scaledStrokeWidth,
            )
        elif self.fill:
            pygame.draw.line(
                screen,
                self.fill,
                utils.worldspace_to_screenspace(self.start, self.customMap),
                utils.worldspace_to_screenspace(self.end, self.customMap),
                1,
            )

    def _applyToScreenGfx(self, screen):
        # Note: aaline() isn't actually from gfxdraw,
        # it just seemed nicer to keep all the AA options toggleable together

        if self.stroke and self.stroke_width:
            pygame.draw.aaline(
                screen,
                self.fill,
                utils.worldspace_to_screenspace(self.start, self.customMap),
                utils.worldspace_to_screenspace(self.end, self.customMap),
                self.scaledStrokeWidth,
            )
        elif self.fill:
            pygame.draw.aaline(
                screen,
                self.fill,
                utils.worldspace_to_screenspace(self.start, self.customMap),
                utils.worldspace_to_screenspace(self.end, self.customMap),
            )

    def applyToScreen(self, screen):
        if USE_PYGAME_GFX:
            self._applyToScreenGfx(screen)
        else:
            self._applyToScreen(screen)


class Polygon(Colorable):
    verts: np.array

    def initFromKwargs(self, **kwargs):
        self.verts = kwargs.get("verts")
        self.points = [None] * len(self.verts)
        super().initFromKwargs(**kwargs)

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.verts = [
            (
                pos[0] + amount * (v[0] - pos[0]),
                pos[1] + amount * (v[1] - pos[1]),
            )
            for v in self.verts
        ]
        super().scaleAtPosition(amount, pos=pos)

    def calculatePoints(self):
        try:
            tmp = self.rotation, self.position
        except:
            return
        for i, v in enumerate(self.verts):
            self.points[i] = utils.worldspace_to_screenspace(
                local_space_to_world_space(v, self.rotation, self.position),
                self.customMap,
            )

    def _applyToScreen(self, screen):
        if self.fill:
            pygame.draw.polygon(screen, self.fill, self.points)
        if self.stroke and self.stroke_width:
            pygame.draw.polygon(screen, self.stroke, self.points, self.scaledStrokeWidth)

    def _applyToScreenGfx(self, screen):
        import pygame.gfxdraw

        if self.fill:
            pygame.gfxdraw.aapolygon(screen, self.points, self.fill)
            pygame.gfxdraw.filled_polygon(screen, self.points, self.fill)

        if self.stroke and self.stroke_width:
            stroke_width = self.scaledStrokeWidth

            if stroke_width > 1:
                pygame.draw.polygon(screen, self.stroke, self.points, stroke_width)
            else:
                pygame.gfxdraw.aapolygon(screen, self.points, self.stroke)
                pygame.gfxdraw.polygon(screen, self.points, self.stroke)

    def applyToScreen(self, screen):
        if USE_PYGAME_GFX:
            self._applyToScreenGfx(screen)
        else:
            self._applyToScreen(screen)

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_poly(physObj.mass, self.verts)
            body = pymunk.Body(
                physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC
            )
        shape = pymunk.Poly(
            body,
            self.verts,
            transform=pymunk.Transform(
                a=np.cos(physObj.rotation),
                b=np.sin(physObj.rotation),
                c=-np.sin(physObj.rotation),
                d=np.cos(physObj.rotation),
                tx=rel_pos[0],
                ty=rel_pos[1],
            ),
        )
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        shape.sensor = physObj.sensor
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY

        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape


class Rectangle(Polygon):
    width: float
    height: float

    def initFromKwargs(self, **kwargs):
        self.width = kwargs.get("width", 20)
        self.height = kwargs.get("height", 20)
        kwargs["verts"] = [
            [self.width / 2, self.height / 2],
            [-self.width / 2, self.height / 2],
            [-self.width / 2, -self.height / 2],
            [self.width / 2, -self.height / 2],
        ]
        super().initFromKwargs(**kwargs)


class Circle(Colorable):
    radius: float

    def initFromKwargs(self, **kwargs):
        self.radius = kwargs.get("radius", 20)
        super().initFromKwargs(**kwargs)

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.radius *= amount
        super().scaleAtPosition(amount, pos=pos)

    def calculatePoints(self):
        try:
            tmp = self.radius
        except:
            return
        self.point = utils.worldspace_to_screenspace(self.position, self.customMap)
        if self.customMap is None:
            self.v_radius = int(
                ScreenObjectManager.instance.SCREEN_HEIGHT / ScreenObjectManager.instance.MAP_HEIGHT * self.radius
            )
            self.h_radius = int(
                ScreenObjectManager.instance.SCREEN_WIDTH / ScreenObjectManager.instance.MAP_WIDTH * self.radius
            )
        else:
            self.v_radius = int(self.customMap["SCREEN_HEIGHT"] / self.customMap["MAP_HEIGHT"] * self.radius)
            self.h_radius = int(self.customMap["SCREEN_WIDTH"] / self.customMap["MAP_WIDTH"] * self.radius)
        self.rect = pygame.Rect(
            self.point[0] - self.h_radius, self.point[1] - self.v_radius, self.h_radius * 2, self.v_radius * 2
        )

    def _applyToScreen(self, screen):
        if self.fill:
            pygame.draw.ellipse(screen, self.fill, self.rect)
        if self.stroke and self.stroke_width:
            pygame.draw.ellipse(screen, self.stroke, self.rect, self.scaledStrokeWidth)

    def _applyToScreenGfx(self, screen):
        import pygame.gfxdraw

        if self.fill and self.stroke and self.stroke_width:
            stroke_width = self.scaledStrokeWidth

            pygame.gfxdraw.aaellipse(screen, *self.point, self.h_radius, self.v_radius, self.stroke)
            pygame.gfxdraw.filled_ellipse(screen, *self.point, self.h_radius, self.v_radius, self.stroke)

            # Assumes stroke_width >= radius implies fill with stroke colour
            h_fill_radius = max(int(self.h_radius - stroke_width), 0)
            v_fill_radius = max(int(self.v_radius - stroke_width), 0)

            if h_fill_radius and v_fill_radius:
                pygame.gfxdraw.aaellipse(screen, *self.point, h_fill_radius, v_fill_radius, self.fill)
                pygame.gfxdraw.filled_ellipse(screen, *self.point, h_fill_radius, v_fill_radius, self.fill)
        elif self.fill:
            pygame.gfxdraw.aaellipse(screen, *self.point, self.h_radius, self.v_radius, self.fill)
            pygame.gfxdraw.filled_ellipse(screen, *self.point, self.h_radius, self.v_radius, self.fill)
        elif self.stroke and self.stroke_width:
            # No fill but still stroke and stroke width. Can't use gfxdraw.
            self._applyToScreen(screen)

    def applyToScreen(self, screen):
        if USE_PYGAME_GFX:
            self._applyToScreenGfx(screen)
        else:
            self._applyToScreen(screen)

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_circle(physObj.mass, 0, self.radius)
            body = pymunk.Body(
                physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC
            )
        shape = pymunk.Circle(body, self.radius, offset=[float(v) for v in rel_pos])
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        shape.sensor = physObj.sensor
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY

        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape


class Arc(Polygon):
    """
    An Arc is just a circle which only has a pie portion drawn.

    However pygame filled arcs (or thick arcs) aren't drawn well. So just use a polygon!
    """

    def initFromKwargs(self, **kwargs):
        self.radius = kwargs.get("radius", 1)
        self.angle_span = kwargs.get("angle", 90)
        kwargs["verts"] = [
            [self.radius * np.cos(x * np.pi / 180), self.radius * np.sin(x * np.pi / 180)]
            for x in range(int(self.angle_span))
        ]
        super().initFromKwargs(**kwargs)
        if self.fill is not None:
            raise ValueError("Arcs are only for strokes.")
        # Actually fill it though.
        self.stroke, self.fill = self.fill, self.stroke
        # But actually, we want to double back so we draw the stroke correctly.
        self.verts = [
            [
                (self.radius + self.stroke_width / 2) * np.cos(x * np.pi / 180 * (-1 if self.angle_span < 0 else 1)),
                (self.radius + self.stroke_width / 2) * np.sin(x * np.pi / 180 * (-1 if self.angle_span < 0 else 1)),
            ]
            for x in range(abs(self.angle_span) + 1)
        ] + [
            [
                (self.radius - self.stroke_width / 2) * np.cos(x * np.pi / 180 * (-1 if self.angle_span < 0 else 1)),
                (self.radius - self.stroke_width / 2) * np.sin(x * np.pi / 180 * (-1 if self.angle_span < 0 else 1)),
            ]
            for x in range(abs(self.angle_span), -1, -1)
        ]
        self.points = [None] * len(self.verts)
        self.calculatePoints()


class Text(Colorable):
    font_style: str
    font_size: int
    _text: str

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self.calculatePoints()

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        from ev3sim.file_helper import find_abs

        self.font_style = kwargs.get("font_style", "fonts/OpenSans-SemiBold.ttf")
        self.font_path = find_abs(self.font_style, allowed_areas=asset_locations())
        self.font_size = kwargs.get("font_size", 30)
        self.hAlignment = kwargs.get("hAlignment", "l")
        self.vAlignment = kwargs.get("vAlignment", "t")
        self.text = kwargs.get("text", "Test")

    def scaleAtPosition(self, amount, pos=(0, 0)):
        self.font_size = int(self.font_size * amount)
        super().scaleAtPosition(amount, pos=pos)

    def calculatePoints(self):
        if self.customMap is None:
            relative_scale = ScreenObjectManager.instance.relativeScreenScale()
            # In order to have a reasonably sized image at all resolutions, calculate the scale to use based on the starting screen scale as well.
            relative_scale = relative_scale * ScreenObjectManager.instance.original_SCREEN_WIDTH / 1280
        else:
            relative_scale = self.customMap["SCREEN_WIDTH"] / 1280 * 293.3 / self.customMap["MAP_WIDTH"]
        new_font_size = int(self.font_size * relative_scale)
        # Scale the font size as much as possible
        relative_scale = self.font_size * relative_scale / new_font_size
        self.font = pygame.freetype.Font(self.font_path, new_font_size)
        self.surface, self.rect = self.font.render(self.text, fgcolor=self.fill)
        self.surface = pygame.transform.scale(
            self.surface,
            (int(self.surface.get_width() * relative_scale), int(self.surface.get_height() * relative_scale)),
        )
        self.screen_size = (self.surface.get_width(), self.surface.get_height())
        baseline = np.array([self.rect.x * relative_scale, self.rect.y * relative_scale])
        self.rect.move_ip(-self.rect.x, -self.rect.y)
        width, height = (
            self.font.get_rect(self.text).width * relative_scale,
            self.font.get_rect(self.text).height * relative_scale,
        )
        self.anchor = utils.worldspace_to_screenspace(self.position, self.customMap)
        if self.hAlignment == "l":
            pass
        elif self.hAlignment == "m":
            self.anchor -= np.array([width / 2.0, 0.0])
        elif self.hAlignment == "r":
            self.anchor -= np.array([width, 0.0])
        else:
            raise ValueError(f"hAlignment is incorrect: {self.hAlignment}")
        if self.vAlignment == "t":
            self.anchor -= np.array([0.0, 0.0])
        elif self.vAlignment == "m":
            self.anchor -= np.array([0.0, height / 2])
        elif self.vAlignment == "baseline":
            self.anchor -= np.array([0.0, baseline[1]])
        elif self.vAlignment == "b":
            self.anchor -= np.array([0.0, height])
        else:
            raise ValueError(f"vAlignment is incorrect: {self.vAlignment}")
        self.rect.move_ip(*self.anchor)

    def applyToScreen(self, screen):
        screen.blit(self.surface, self.rect)

    def getPositionAnchorOffset(self):
        res = np.array([0.0, 0.0])
        from ev3sim.visual.utils import screenspace_to_worldspace

        if self.customMap is None:
            physics_size = screenspace_to_worldspace(
                [
                    ScreenObjectManager.instance._SCREEN_WIDTH_ACTUAL / 2 + self.screen_size[0],
                    ScreenObjectManager.instance._SCREEN_HEIGHT_ACTUAL / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        else:
            physics_size = screenspace_to_worldspace(
                [
                    self.customMap["SCREEN_WIDTH"] / 2 + self.screen_size[0],
                    self.customMap["SCREEN_HEIGHT"] / 2 + self.screen_size[1],
                ],
                self.customMap,
            )
        if self.hAlignment == "l":
            res += np.array([physics_size[0] / 2, 0.0])
        elif self.hAlignment == "m":
            pass
        elif self.hAlignment == "r":
            res -= np.array([physics_size[0] / 2, 0.0])
        else:
            raise ValueError(f"hAlignment is incorrect: {self.hAlignment}")
        if self.vAlignment == "t":
            res += np.array([0.0, physics_size[1] / 2])
        elif self.vAlignment == "m":
            pass
        elif self.vAlignment == "b":
            res -= np.array([0.0, physics_size[1] / 2])
        else:
            raise ValueError(f"vAlignment is incorrect: {self.vAlignment}")
        return res


def visualFactory(**options):
    if "name" not in options:
        raise ValueError("Tried to generate visual element, but no 'name' field was supplied.")
    for klass in (Polygon, Rectangle, Circle, Arc, Text, Image):
        if options["name"] == klass.__name__:
            r = klass(**options)
            return r
    name = options["name"]
    raise ValueError(f"Unknown visual element, {name}")
