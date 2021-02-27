class EditWatcher:
    '''
    Proxy for watch changes in object.
    If any attribute in object is changed
    then @is_edited return True.

    Example
    =======
    class MyClass:
        def __init__(self):
            self.prop = 0

    obj = MyClass()
    watcher = EditWatcher(obj)
    print(watcher.prop, obj.prop, watcher.is_edited)
    > 0 0 False
    watcher.prop = 1
    print(watcher.prop, obj.prop, watcher.is_edited)
    > 1 1 True
    '''

    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_edited", False)

    def __getattr__(self, key):
        return getattr(self._obj, key)

    def __setattr__(self, name, value):
        object.__setattr__(self, "_edited", True)
        return setattr(self._obj, name, value)

    def __getitem__(self, key):
        return self._obj[key]

    def __setitem__(self, key, value):
        object.__setattr__(self, "_edited", True)
        self._obj[key] = value

    @property
    def is_edited(self):
        return self._edited

    def get_wrapped(self):
        return self._obj
