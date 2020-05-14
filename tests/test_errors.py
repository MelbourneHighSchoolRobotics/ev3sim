import pytest

from visual.objects import visualFactory

def test_visual_factory():
    with pytest.raises(ValueError) as e:
        visualFactory(**{})
