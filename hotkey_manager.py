import keyboard
from PySide6.QtCore import QObject, Signal

class HotkeyListener(QObject):
    """A QObject to run the hotkey listener in a separate thread."""
    show_window_signal = Signal()

    def __init__(self, hotkey_config):
        super().__init__()
        self.hotkey_config = hotkey_config
        self.hotkey_ref = None

    def on_show_window(self):
        """Callback for the show window hotkey."""
        self.show_window_signal.emit()

    def run(self):
        """Registers hotkeys."""
        try:
            show_hotkey = self.hotkey_config.get('show_window', 'alt+space')
            # Remove previous hotkey if any, before adding a new one.
            if self.hotkey_ref:
                keyboard.remove_hotkey(self.hotkey_ref)
            self.hotkey_ref = keyboard.add_hotkey(show_hotkey, self.on_show_window, suppress=True)
            print(f"Registered hotkey: {show_hotkey}")
        except Exception as e:
            print(f"Failed to register hotkey: {e}")

    def stop(self):
        """Stops the hotkey listener."""
        try:
            if self.hotkey_ref:
                keyboard.remove_hotkey(self.hotkey_ref)
                self.hotkey_ref = None
                print("Hotkey listener stopped and hotkey removed.")
        except Exception as e:
            print(f"Error removing hotkey: {e}")