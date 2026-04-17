
import logging
import tkinter as tk

class TextLoggerHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        self.widget.after(0, self._append_output, msg)
    
    def _append_output(self, msg):
        self.widget.config(state='normal')
        self.widget.insert(tk.END, msg + '\n')
        self.widget.config(state='disabled')
        self.widget.see(tk.END)
