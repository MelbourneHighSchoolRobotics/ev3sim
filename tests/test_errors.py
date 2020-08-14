import pytest

from ev3sim.visual.objects import visualFactory

def test_visual_factory():
    with pytest.raises(ValueError) as e:
        visualFactory(**{})
