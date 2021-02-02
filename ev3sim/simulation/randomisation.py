# Singleton instance for generating random numbers, so it can be globally seeded and keep multiple random instances available
import numpy.random as rd


class Randomiser:

    instance: "Randomiser" = None

    def __init__(self, seed):
        self.global_random = rd.RandomState(seed)
        self.__class__.instance = self
        self.port_randomisers = {}
        self.seeds = {}

    @classmethod
    def createGlobalRandomiserWithSeed(cls, seed):
        r = Randomiser(seed)

    @classmethod
    def _stringToSeed(cls, string):
        import hashlib

        # Random unsigned int of size 32 (8*4).
        return int(hashlib.sha512(string.encode("utf-8")).hexdigest()[:8], 16)

    @classmethod
    def createPortRandomiserWithSeed(cls, port_key, seed=None):
        instance = cls.getInstance()
        if port_key in instance.port_randomisers:
            # This shouldn't error out, the code will likely fail instead.
            return instance.port_randomisers[port_key]
        seed = cls._stringToSeed(port_key) if seed is None else seed
        instance.port_randomisers[port_key] = rd.RandomState(seed=seed)
        instance.seeds[port_key] = seed
        return instance.port_randomisers[port_key]

    @classmethod
    def getInstance(cls):
        if cls.instance is not None:
            return cls.instance
        raise ValueError("Attempted to get random instance but none has been created.")

    @classmethod
    def getGlobalRandom(cls):
        instance = cls.getInstance()
        return instance.global_random

    @classmethod
    def getPortRandom(cls, port_key):
        instance = cls.getInstance()
        return instance.port_randomisers[port_key]

    @classmethod
    def random(cls):
        r = cls.getGlobalRandom()
        return r.random()
