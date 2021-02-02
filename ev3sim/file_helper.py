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
    from ev3sim.simulation.loader import StateHandler

    if StateHandler.WORKSPACE_FOLDER:
        WORKSPACE = os.path.abspath(StateHandler.WORKSPACE_FOLDER)
    else:
        WORKSPACE = ""

    fnames = split_names(filepath)
    if allowed_areas is None:
        allowed_areas = ["workspace", "local", "package"]
    for area in allowed_areas:
        if area == "package":
            path = os.path.join(ROOT, *fnames)
        elif area.startswith("package"):
            path = os.path.join(ROOT, *area[8:].replace("\\", "/").split("/"), *fnames)
        elif area == "workspace":
            if not WORKSPACE:
                continue
            path = os.path.join(WORKSPACE, *fnames)
        elif area.startswith("workspace"):
            if not WORKSPACE:
                continue
            path = os.path.join(WORKSPACE, *area[10:].replace("\\", "/").split("/"), *fnames)
        elif area == "local":
            path = filepath
        elif area.startswith("local"):
            path = os.path.join(*area[6:].replace("\\", "/").split("/"), *fnames)
        else:
            raise ValueError(f"Unknown file area {area}")
        if os.path.isdir(path) or os.path.isfile(path):
            return path
    raise ValueError(f"File not found: {filepath}")


def find_abs_directory(dirpath, create=False):
    try:
        return find_abs("", allowed_areas=[dirpath])
    except ValueError as e:
        if not create:
            raise e
        else:
            # Remove one part of the directory, then try again.
            rest, single = os.path.split(dirpath.rstrip("/"))
            if rest == dirpath:
                raise ValueError(f"Find abs dir failed with input {dirpath}")
            dirname = find_abs_directory(rest, create=create)
            fpath = os.path.join(dirname, single)
            os.mkdir(fpath)
            return fpath
