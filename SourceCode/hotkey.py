from pynput import keyboard
class Hotkey: 
    __registry = []
    def __init__(self, keys: str | keyboard.Key, function: callable, args: tuple[tuple[str , any]], protected: bool = False,name: str = None) -> None:
        self.name = name if name is not None else function.__name__
        self.__registry.append(self)
        for key in keys:
            if isinstance(key, str):
                if key.startswith("Key."):
                    keys = [keyboard.Key[key[4:]] if k == key else k for k in keys]
        self.keys = set(keys)
        if isinstance(keys, (str, keyboard.Key)):
            self.keys = {keys}
        else:
            self.keys = set(keys)
        self.function = function
        self.args = args
        self.protected = protected
        
    @classmethod
    def getRegistry(cls) -> list:
        """Gibt die Liste aller registrierten Hotkeys zurück. Diese Methode kann verwendet werden, um alle Hotkeys zu überprüfen oder zu debuggen."""
        return cls.__registry
    
    @classmethod
    def clearRegistry(cls) -> None:
        """Löscht alle registrierten Hotkeys. Diese Methode sollte mit Vorsicht verwendet werden, da sie alle Hotkeys entfernt, einschließlich der geschützten."""
        cls.__registry.clear() 
        
    def isPressed(self, activeKeys : tuple[str | keyboard.Key]) -> bool:
        if len(self.keys) != len(activeKeys):
            return False
        check = all(key in activeKeys for key in self.keys)
        if check:
            return True
        elif self.keys.__str__() == activeKeys.__str__():
            return True
        return False
    
    def execute(self) -> None:
        print(f"Executing function for hotkey: {self.keys}")
        kwarg_dict = dict(self.args)
        self.function(**kwarg_dict)
        
    def remove(self) -> None:
        if self.protected:
            print(f"Hotkey {self.keys} is protected and cannot be removed.")
            return
        self.__registry.remove(self)
        del self
    def setFunction(self, function: callable, *args) -> None:
        self.function = function
        self.args = args
        