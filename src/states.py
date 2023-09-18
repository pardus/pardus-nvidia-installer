class PackageProgressState:
    def __init__(self):
        self._value = 0
        self._observers = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if self._value != new_value:
            self._value = new_value
            self.notify_observers(new_value)

    def add_observer(self, observer):
        self._observers.append(observer)

    def notify_observers(self, new_value):
        for observer in self._observers:
            observer(new_value)


pkg_ins_progress: PackageProgressState = PackageProgressState()
