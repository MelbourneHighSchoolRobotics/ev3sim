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
