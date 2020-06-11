class IInteractor:

    constants: dict

    def __init__(self, **kwargs):
        pass

    def startUp(self):
        pass

    # tick returns a boolean, which is true if the script should end.
    def tick(self, tick) -> bool:
        raise NotImplementedError(f"Interactor Interface {self.__cls__} doesn't implement method tick")

    def tearDown(self):
        pass
