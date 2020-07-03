import numpy as np

class Collider:
    
    obj: 'objects.base.PhysicsObject' # noqa: F821

    def __init__(self, obj):
        self.physicsObject = obj

    def generateExtraPhysicsAttributes(self):
        raise NotImplementedError("Collider does not implement generateExtraPhysicsAttributes")

    def getCollisionInfo(self, other: 'Collider'):
        raise NotImplementedError("Collider does not implement getCollisionInfo")

    def initFromKwargs(self, **kwargs):
        pass

class Circle(Collider):

    radius: float

    def generateExtraPhysicsAttributes(self):
        self.physicsObject.inertia = 0.5 * self.physicsObject.mass * self.radius * self.radius

    def getCollisionInfo(self, other: Collider):
        if isinstance(other, Circle):
            displacement_vector = other.physicsObject.position - self.physicsObject.position
            distance = np.sqrt(pow(displacement_vector[0], 2) + pow(displacement_vector[1], 2))
            if distance < self.radius + other.radius:
                return {
                    'collision': True,
                    'world_space_position': displacement_vector * (self.radius / distance - 0.5*(1 - distance / (self.radius + other.radius))) + self.physicsObject.position,
                    'distance_collided': self.radius + other.radius - distance
                }
            return {
                'collision': False,
                'world_space_position': None,
                'distance_collided': None
            }
        if isinstance(other, ConvexPolygon):
            # Find the closest intersection with the circle for each edge on the rectangle
            best_distance = self.radius + 100
            best_point = None
            for a, b in zip(other.verts[:-1], other.verts[1:]):
                # Vector from a to b, now in worldspace
                ws_b = np.array([
                    b[0] * np.cos(other.physicsObject.rotation) - b[1] * np.sin(other.physicsObject.rotation),
                    b[1] * np.cos(other.physicsObject.rotation) + b[0] * np.sin(other.physicsObject.rotation),
                ]) + other.physicsObject.position[:2]
                ws_a = np.array([
                    a[0] * np.cos(other.physicsObject.rotation) - a[1] * np.sin(other.physicsObject.rotation),
                    a[1] * np.cos(other.physicsObject.rotation) + a[0] * np.sin(other.physicsObject.rotation),
                ]) + other.physicsObject.position[:2]
                ws_vec = ws_b - ws_a
                a_to_circle = self.physicsObject.position[:2] - ws_a
                edge_length = np.sqrt(pow(ws_vec[0], 2) + pow(ws_vec[1], 2))
                edge_normalize = ws_vec / edge_length
                dotP = np.dot(a_to_circle, edge_normalize)
                if dotP < 0:
                    # Closest point is vertex a.
                    intersection_point = ws_a
                elif dotP > edge_length:
                    # Closest point is vertex b.
                    intersection_point = ws_b
                else:
                    # Closest point is ws_a + dotP * edge_normalize
                    intersection_point = ws_a + edge_normalize * dotP
                vec = intersection_point - self.physicsObject.position[:2]
                d = np.sqrt(pow(vec[0], 2) + pow(vec[1], 2))
                if d < best_distance:
                    best_distance = d
                    best_point = intersection_point
                    best_point = np.append(best_point, np.array([self.physicsObject.position[2]]))
            if best_distance < self.radius:
                return {
                    'collision': True,
                    'world_space_position': best_point,
                    'distance_collided': self.radius - best_distance
                }
            return {
                'collision': False,
                'world_space_position': None,
                'distance_collided': None
            }
        raise ValueError(f"Collision not handled: Circle to {str(other)}")

    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.radius = kwargs.get('radius', 100)

class ConvexPolygon(Collider):

    # These verts are defined relative to the centroid at 0,0.
    # Vertices should move counter-clockwise around the centroid, and include the first vertex at the start and end.
    verts: np.array

    def generateExtraPhysicsAttributes(self):
        # Generate inertia for each tri
        i = 0
        for a, b in zip(self.verts[:-1], self.verts[1:]):
            i += (pow(a[0], 2) + pow(a[1], 2) + pow(b[0], 2) + pow(b[1], 2) + np.dot(a, b)) / 6
        self.physicsObject.inertia = i * self.physicsObject.mass
    
    def getCollisionInfo(self, other: Collider):
        if isinstance(other, Circle):
            return other.getCollisionInfo(self)
        else:
            # TODO: Handle collisions between two convex polygons
            return {
                'collision': False,
                'world_space_position': None,
                'distance_collided': None
            }
    
    def initFromKwargs(self, **kwargs):
        super().initFromKwargs(**kwargs)
        self.verts = np.array(kwargs.get('verts', [(0, 1), (-1, 0), (0, -1), (1, 0), (0, 1)]))

def colliderFactory(physObj, **options):
    if 'name' not in options:
        raise ValueError("Tried to generate collider, but no 'name' field was supplied.")
    for klass in (Circle, ConvexPolygon):
        if options['name'] == klass.__name__:
            r = klass(physObj)
            r.initFromKwargs(**options)
            return r
    name = options['name']
    raise ValueError(f"Unknown collider, {name}")
