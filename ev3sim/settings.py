class BindableValue:
    """
    A value which can be bound and exposes methods for on change of this value.
    """

    def __init__(self, default):
        self._value = default

    def on_change(self, new_value):
        pass

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if self._value != new_value:
            self.on_change(new_value)
        self._value = new_value


class ObjectSetting(BindableValue):
    """
    Particular bindable value which is bound to the attribute of an object.
    """

    def __init__(self, object, attr):
        super().__init__(getattr(object, attr, None))
        self.obj = object
        self.attr = attr

    def __str__(self):
        return f"Setting {self.obj}[{self.attr}]"

    def on_change(self, new_value):
        super().on_change(new_value)
        setattr(self.obj, self.attr, new_value)


class SettingsManager:
    """
    A singleton which keeps track of the settings derived from all areas.
    """

    instance: "SettingsManager" = None

    def __init__(self):
        self.settings = {}
        SettingsManager.instance = self

    def addSetting(self, setting_name, setting_value):
        assert setting_name not in self.settings, "Settings under this name are already defined."
        self.settings[setting_name] = setting_value

    def addSettingGroup(self, group_name, settings_definition):
        assert group_name not in self.settings, "Settings under this name are already defined."
        self.settings[group_name] = settings_definition

    def removeSetting(self, name):
        del self.settings[name]

    def setMany(self, settings_obj, append_keys=None):
        if append_keys is None:
            append_keys = []
        for key in settings_obj:
            if isinstance(settings_obj[key], dict):
                # group.
                self.setMany(settings_obj[key], append_keys + [key])
            else:
                self[append_keys + [key]].value = settings_obj[key]

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.settings[key]
        cur = self.settings
        for subkey in key:
            cur = cur[subkey]
        return cur

    def __setitem__(self, key, value):
        if isinstance(key, str):
            self.settings[key].value = value
            return
        cur = self.settings
        for subkey in key:
            cur = cur[subkey]
        cur.value = value
