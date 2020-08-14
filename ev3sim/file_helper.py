import os

ROOT = os.path.abspath(os.path.dirname(__file__))

def find_abs(filename, allowed_areas=None):
    """
    Attempt to find a reference file, from this list of appropriate places specified.
    
    allowed_areas can contain:
        - package: search from root level of package
        - package/path: search from path in package
        - local: search from where the script is executed
        - local/path: search from path in script execution
    
    areas leftmost will be considered first.
    this defaults to local, then package.
    """
    if allowed_areas is None:
        allowed_areas = ['local', 'package']
    for area in allowed_areas:
        if area == 'package':
            path = os.path.join(ROOT, filename)
        elif area.startswith('package'):
            path = os.path.join(ROOT, area[8:], filename)
        elif area == 'local':
            path = filename
        elif area.startswith('local'):
            path = os.path.join(ROOT, area[6:], filename)
        else:
            raise ValueError(f'Unknown file area {area}')
        if os.path.isdir(path) or os.path.isfile(path):
            return path
    raise ValueError(f'File not found: {filename}')
