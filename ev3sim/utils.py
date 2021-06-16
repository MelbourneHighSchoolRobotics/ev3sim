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
    from luddite import get_version_pypi

    q._internal_size = i
    try:
        v = get_version_pypi("ev3sim")
        q.put(v)
    except:
        q.put(__version__)


def checkVersion():
    from multiprocessing import Process
    from ev3sim import __version__
    from ev3sim.visual.manager import ScreenObjectManager

    Q = Queue()
    process = Process(target=_latest_version, args=(Q, Q._internal_size))
    process.start()
    process.join(2)
    if process.is_alive():
        process.terminate()
        ScreenObjectManager.NEW_VERSION = False
    else:
        ScreenObjectManager.NEW_VERSION = Q.get() != __version__
