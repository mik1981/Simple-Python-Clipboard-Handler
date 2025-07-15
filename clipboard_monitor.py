import threading
import time
import pyperclip

class ClipboardMonitor(threading.Thread):
    def __init__(self, callback, poll_interval=0.5):
        super().__init__()
        self.callback = callback
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self.last_text = None

    def run(self):
        while not self._stop_event.is_set():
            try:
                text = pyperclip.paste()
                if text != self.last_text and text.strip():
                    self.last_text = text
                    self.callback(text)
            except Exception as e:
                pass
            time.sleep(self.poll_interval)

    def stop(self):
        self._stop_event.set()
