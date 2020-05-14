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
