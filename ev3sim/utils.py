import multiprocessing
from multiprocessing.queues import Queue as BaseQueue


class Queue(BaseQueue):
    """
    Multiprocessing queue that has a stable qsize value, and supports these methods for OSX.
    Also taken from https://github.com/vterron/lemon/commit/9ca6b4b1212228dbd4f69b88aaf88b12952d7d6f
    """

    def __init__(self, *args, **kwargs):
        self._internal_size = multiprocessing.Value("i", 0)
        if "ctx" not in kwargs:
            kwargs["ctx"] = multiprocessing.get_context()
        super().__init__(*args, **kwargs)

    def put(self, *args, **kwargs):
        with self._internal_size.get_lock():
            self._internal_size.value += 1
        super().put(*args, **kwargs)

    def get(self, *args, **kwargs):
        res = super().get(*args, **kwargs)
        # Ensure the size only decrements once the element has been gained.
        with self._internal_size.get_lock():
            self._internal_size.value -= 1
        return res

    def qsize(self):
        return self._internal_size.value

    def empty(self):
        return not self.qsize()


def recursive_merge(dict1, dict2):
    # Recursively merge two dictionaries into dict1.
    for key in dict2:
        if key not in dict1 or type(dict1[key]) != type(dict2[key]):
            dict1[key] = dict2[key]
        elif isinstance(dict2[key], dict):
            # Recursively merge.
            recursive_merge(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]


def _latest_version(q, i):
    from ev3sim import __version__
    import requests

    q._internal_size = i
    try:
        r = requests.get("https://pypi.org/pypi/ev3sim/json")
        j = r.json()
        v = j["info"]["version"]
        q.put(v)
    except:
        q.put(__version__)


def canUpdate():
    from multiprocessing import Process
    from ev3sim import __version__

    Q = Queue()
    process = Process(target=_latest_version, args=(Q, Q._internal_size))
    process.start()
    process.join(2)
    if process.is_alive():
        process.terminate()
        return False
    else:

        def transform_to_list(version_string):
            s = version_string.split(".")
            for x in range(len(s)):
                try:
                    s[x] = int(s[x])
                except:
                    # This ensures that an ordering can be made.
                    # If the version number is text, we can assume this is a development version,
                    # and so updates that match previous numbers but not the last don't need to be updated.
                    s[x] = 9999
            return s

        online_version = transform_to_list(Q.get())
        local_version = transform_to_list(__version__)
        return online_version > local_version


APP_VSCODE = "VSCODE"
APP_MINDSTORMS = "MINDSTORMS"
APP_EXPLORER = "EXPLORER"


def open_file(filepath, pref_app, folder=""):
    import os
    import platform
    import subprocess

    if pref_app != APP_EXPLORER:
        # Try opening with vs or mindstorms
        if platform.system() == "Windows":
            paths = [
                os.path.join(os.environ["ALLUSERSPROFILE"], "Microsoft", "Windows", "Start Menu", "Programs"),
                os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"),
            ]
            for path in paths:
                if os.path.exists(path):
                    for fd in os.listdir(path):
                        if pref_app == APP_VSCODE and "Visual Studio Code" in fd:
                            f = os.path.join(path, fd)
                            for file in os.listdir(f):
                                if folder:
                                    subprocess.run(
                                        f'start "code" "{os.path.join(f, file)}" ""{folder}" --goto "{filepath}""',
                                        shell=True,
                                    )
                                else:
                                    subprocess.run(
                                        f'start "code" "{os.path.join(f, file)}" ""{filepath}""',
                                        shell=True,
                                    )
                                return
                        if pref_app == APP_MINDSTORMS and "MINDSTORMS" in fd:
                            f = os.path.join(path, fd)
                            for file in os.listdir(f):
                                subprocess.run(
                                    f'start "{os.path.join(f, file)}" "{filepath}"',
                                    shell=True,
                                )
                                return

    if platform.system() == "Windows":
        subprocess.Popen(["explorer", "/select,", filepath])
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", filepath])
    else:
        subprocess.Popen(["xdg-open", filepath])
    return
