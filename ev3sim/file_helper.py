import os

ROOT = os.path.abspath(os.path.dirname(__file__))


def split_names(path):
    names = []
    while True:
        name1, name2 = os.path.split(path)
        if name1 == path:
            names.append(name1)
            break
        if name2 == path:
            names.append(name2)
            break
        path = name1
        names.append(name2)
    return names[::-1]


def find_abs(filepath, allowed_areas=None):
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
    fnames = split_names(filepath)
    if allowed_areas is None:
        allowed_areas = ["local", "package"]
    for area in allowed_areas:
        if area == "package":
            path = os.path.join(ROOT, *fnames)
        elif area.startswith("package"):
            path = os.path.join(ROOT, *area[8:].replace("\\", "/").split("/"), *fnames)
        elif area == "local":
            path = filepath
        elif area.startswith("local"):
            path = os.path.join(*area[6:].replace("\\", "/").split("/"), *fnames)
        else:
            raise ValueError(f"Unknown file area {area}")
        if os.path.isdir(path) or os.path.isfile(path):
            return path
    raise ValueError(f"File not found: {filepath}")
