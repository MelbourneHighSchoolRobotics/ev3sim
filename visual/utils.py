from typing import Tuple
def hex_to_pycolor(hex_str: str) -> Tuple[int]:
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    assert len(hex_str) == 6, f"Invalid hex string, #{hex_str}"
    return (
        int(hex_str[:2], 16),
        int(hex_str[2:4], 16),
        int(hex_str[4:], 16)
    )

def worldspace_to_screenspace(point):
    from visual.manager import ScreenObjectManager
    return (
        int(point[0] * ScreenObjectManager.instance.screen_width / ScreenObjectManager.instance.map_width + ScreenObjectManager.instance.screen_width / 2),
        int(-point[1] * ScreenObjectManager.instance.screen_height / ScreenObjectManager.instance.map_height + ScreenObjectManager.instance.screen_height / 2),
    )
