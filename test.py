# This is TEMPORARY

from simulation.loader import ScriptLoader
from tests.random_testing import RandomInteractor

sl = ScriptLoader()
sl.startUp()
sl.simulate(RandomInteractor(**{'visual': {
            'name': 'Circle',
            'radius': 20,
            'fill': '#ff00ff',
            'stroke': '#aaaaaa',
            'stroke_width': 3,
        },
        'children': [
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 2,
                },
                'position': (15, 0, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'stroke': '#ff0000',
                    'stroke_width': 2,
                },
                'position': (-15, 0, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 20,
                    'height': 10,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 2,
                },
                'position': (0, 15, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 20,
                    'height': 10,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 2,
                },
                'position': (0, -15, 1)
            },
        ]}))
