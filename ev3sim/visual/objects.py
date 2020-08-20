import numpy as np
import pygame
import pygame.freetype
import pymunk
from typing import Optional, Tuple

from ev3sim.visual.manager import ScreenObjectManager
import ev3sim.visual.utils as utils
from ev3sim.objects.utils import local_space_to_world_space


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

    def __init__(self, **kwargs):
        self.initFromKwargs(**kwargs)

    def initFromKwargs(self, **kwargs):
        """Initialise the visual object given some extra named arguments (normally provided in the ``.yaml`` files)."""
        self.position = kwargs.get('position', [0, 0])
        self.rotation = kwargs.get('rotation', 0)
        self.zPos = kwargs.get('zPos', 0)
        self.sensorVisible = kwargs.get('sensorVisible', False)
        self.visible = kwargs.get('visible', True)

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

    def applyToScreen(self):
        """
        A method that all visual elements must implement.
        When invoked, should apply themselves to the screen.
        """
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `applyToScreen`")

    def calculatePoints(self):
        """
        Called whenever the position or rotation of the object is changed, allowing for any calculation needed to be made.
        """
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `calculatePoints`")

    def generateBodyAndShape(self, physObj, body=None, rel_pos=None):
        """
        Generates the physics object for this particular visual element. See other implementations of this method for examples.

        :param ev3sim.objects.base.PhysicsObject physObj: The physics object requesting this body and shape.
        :param pymunk.Body body: If you don't want a new body generated, supply one.
        :param tuple rel_pos: If an existing body was specified, then this is the relative position of the shape on the body.
        :returns (pymunk.Body, pymunk.Shape): The generated objects.
        """
        raise NotImplementedError(f"The VisualElement {self.__cls__} does not implement the pivotal method `generateShape`")

class Colorable(IVisualElement):
    _fill: Optional[Tuple[int]]
    _stroke: Optional[Tuple[int]]
    stroke_width: float

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.fill = kwargs.get('fill', '#ffffff')
        self.stroke = kwargs.get('stroke', None)
        self.stroke_width = kwargs.get('stroke_width', 1)

    @property
    def fill(self) -> Tuple[int]:
        return self._fill

    @fill.setter
    def fill(self, value):
        if isinstance(value, str):
            if value in utils.GLOBAL_COLOURS:
                value = utils.GLOBAL_COLOURS[value]
            if value.startswith('#'):
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
            if value.startswith('#'):
                value = value[1:]
            self._stroke = utils.hex_to_pycolor(value)
        else:
            self._stroke = value

class Image(Colorable):

    def initFromKwargs(self, **kwargs):
        self._image_path = ''
        self.image_path = kwargs.get('image_path')
        super().initFromKwargs(**kwargs)
        self.fill = kwargs.get('fill', (0, 0, 0, 0))
        self.calculatePoints()

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        from ev3sim.file_helper import find_abs
        self._image_path = find_abs(value, allowed_areas=['local', 'local/assets/', 'package', 'package/assets/'])
        self.image = pygame.image.load(self._image_path)

    def calculatePoints(self):
        self.rotated = pygame.transform.rotate(self.image, self.rotation * 180 / np.pi)
        self.rotated.fill(self.fill, special_flags=pygame.BLEND_ADD)
        self.screen_location = utils.worldspace_to_screenspace(self.position)
        self.screen_size = self.rotated.get_size()
        self.screen_location = (int(self.screen_location[0] - self.screen_size[0] / 2), int(self.screen_location[1] - self.screen_size[1] / 2))
        from ev3sim.visual.utils import screenspace_to_worldspace
        pos_loc = screenspace_to_worldspace(self.screen_location)
        self.verts = [
            screenspace_to_worldspace([ScreenObjectManager.instance.screen_width / 2 + self.screen_size[0]/2, ScreenObjectManager.instance.screen_height / 2 + self.screen_size[1] / 2]),
            screenspace_to_worldspace([ScreenObjectManager.instance.screen_width / 2 + self.screen_size[0]/2, ScreenObjectManager.instance.screen_height / 2 - self.screen_size[1] / 2]),
            screenspace_to_worldspace([ScreenObjectManager.instance.screen_width / 2 - self.screen_size[0]/2, ScreenObjectManager.instance.screen_height / 2 - self.screen_size[1] / 2]),
            screenspace_to_worldspace([ScreenObjectManager.instance.screen_width / 2 - self.screen_size[0]/2, ScreenObjectManager.instance.screen_height / 2 + self.screen_size[1] / 2]),
        ]

    def applyToScreen(self):
        ScreenObjectManager.instance.screen.blit(self.rotated, self.screen_location)

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_poly(physObj.mass, self.verts)
            body = pymunk.Body(physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC)
        shape = pymunk.Poly(body, self.verts, transform=pymunk.Transform(
            a=np.cos(physObj.rotation), 
            b=np.sin(physObj.rotation), 
            c=-np.sin(physObj.rotation), 
            d=np.cos(physObj.rotation), 
            tx=rel_pos[0],
            ty=rel_pos[1],
        ))
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY
        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape

class Line(Colorable):

    # THESE DON'T HAVE A LOCAL POSITION

    def initFromKwargs(self, **kwargs):
        self.start = kwargs.get('start')
        self.end = kwargs.get('end')
        super().initFromKwargs(**kwargs)

    def calculatePoints(self):
        return

    def applyToScreen(self):
        if self.fill:
            pygame.draw.line(
                ScreenObjectManager.instance.screen, 
                self.fill, 
                utils.worldspace_to_screenspace(self.start),
                utils.worldspace_to_screenspace(self.end),
                1,
            )
        if self.stroke and self.stroke_width:
            pygame.draw.line(
                ScreenObjectManager.instance.screen, 
                self.fill, 
                utils.worldspace_to_screenspace(self.start),
                utils.worldspace_to_screenspace(self.end),
                max(1, int(self.stroke_width * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width)),
            )

class Polygon(Colorable):

    verts: np.array

    def initFromKwargs(self, **kwargs):
        self.verts = kwargs.get('verts')
        self.points = [None]*len(self.verts)
        super().initFromKwargs(**kwargs)

    def calculatePoints(self):
        try:
            tmp = self.rotation, self.position
        except:
            return
        for i, v in enumerate(self.verts):
            self.points[i] = utils.worldspace_to_screenspace(local_space_to_world_space(v, self.rotation, self.position))

    def applyToScreen(self):
        if self.fill:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.fill, self.points)
        if self.stroke and self.stroke_width:
            pygame.draw.polygon(ScreenObjectManager.instance.screen, self.stroke, self.points, max(1, int(self.stroke_width * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width)))

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_poly(physObj.mass, self.verts)
            body = pymunk.Body(physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC)
        shape = pymunk.Poly(body, self.verts, transform=pymunk.Transform(
            a=np.cos(physObj.rotation), 
            b=np.sin(physObj.rotation), 
            c=-np.sin(physObj.rotation), 
            d=np.cos(physObj.rotation), 
            tx=rel_pos[0],
            ty=rel_pos[1],
        ))
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY
        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape

class Rectangle(Polygon):

    width: float
    height: float

    def initFromKwargs(self, **kwargs):
        self.width = kwargs.get('width', 20)
        self.height = kwargs.get('height', 20)
        kwargs['verts'] = [
            [self.width/2, self.height/2],
            [-self.width/2, self.height/2],
            [-self.width/2, -self.height/2],
            [self.width/2, -self.height/2],
        ]
        super().initFromKwargs(**kwargs)

class Circle(Colorable):

    radius: float

    def initFromKwargs(self, **kwargs):
        self.radius = kwargs.get('radius', 20)
        super().initFromKwargs(**kwargs)

    def calculatePoints(self):
        try:
            tmp = self.radius
        except:
            return
        self.point = utils.worldspace_to_screenspace(self.position)
        self.v_radius = int(ScreenObjectManager.instance.screen_height / ScreenObjectManager.instance.map_height * self.radius)

    def applyToScreen(self):
        if self.fill:
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.fill, self.point, self.v_radius)
        if self.stroke and self.stroke_width:
            pygame.draw.circle(ScreenObjectManager.instance.screen, self.stroke, self.point, self.v_radius, max(1, int(self.stroke_width * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width)))

    def generateBodyAndShape(self, physObj, body=None, rel_pos=(0, 0)):
        if body is None:
            moment = pymunk.moment_for_circle(physObj.mass, 0, self.radius)
            body = pymunk.Body(physObj.mass, moment, body_type=pymunk.Body.STATIC if physObj.static else pymunk.Body.DYNAMIC)
        shape = pymunk.Circle(body, self.radius, offset=rel_pos)
        shape.friction = physObj.friction_coefficient
        shape.elasticity = physObj.restitution_coefficient
        shape.collision_type = 1
        from ev3sim.objects.base import STATIC_CATEGORY, DYNAMIC_CATEGORY
        shape.filter = pymunk.ShapeFilter(categories=STATIC_CATEGORY if physObj.static else DYNAMIC_CATEGORY)
        return body, shape

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
        self.font_style = kwargs.get('font_style', pygame.font.get_default_font())
        self.font_size = kwargs.get('font_size', 30)
        self.font = pygame.freetype.SysFont(self.font_style, self.font_size)
        self.hAlignment = kwargs.get('hAlignment', 'l')
        self.vAlignment = kwargs.get('vAlignment', 't')
        self.text = kwargs.get('text', 'Test')

    def calculatePoints(self):
        if not hasattr(self, 'font'):
            return
        self.surface, self.rect = self.font.render(self.text, fgcolor=self.fill)
        self.anchor = utils.worldspace_to_screenspace(self.position)
        if self.hAlignment == 'l':
            pass
        elif self.hAlignment == 'm':
            self.anchor -= np.array([self.font.get_rect(self.text).width / 2.0, 0.0])
        elif self.hAlignment == 'r':
            self.anchor -= np.array([self.font.get_rect(self.text).width, 0.0])
        else:
            raise ValueError(f'hAlignment is incorrect: {self.hAlignment}')
        if self.vAlignment == 't':
            self.anchor -= np.array([0.0, self.font.get_rect(self.text).height / 2.0])
        elif self.vAlignment == 'm':
            self.anchor -= np.array([0.0, self.font.get_rect(self.text).height])
        elif self.vAlignment == 'b':
            self.anchor -= np.array([0.0, 3 * self.font.get_rect(self.text).height / 2.0])
        else:
            raise ValueError(f'vAlignment is incorrect: {self.vAlignment}')
        self.rect.move_ip(*self.anchor)
    
    def applyToScreen(self):
        ScreenObjectManager.instance.screen.blit(self.surface, self.rect)


def visualFactory(**options):
    if 'name' not in options:
        raise ValueError("Tried to generate visual element, but no 'name' field was supplied.")
    for klass in (Polygon, Rectangle, Circle, Text, Image):
        if options['name'] == klass.__name__:
            r = klass(**options)
            return r
    name = options['name']
    raise ValueError(f"Unknown visual element, {name}")
