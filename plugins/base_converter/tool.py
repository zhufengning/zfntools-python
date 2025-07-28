# plugins/base_converter/tool.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit
from PySide6.QtGui import QIntValidator

TOOL_NAME = "进制转换"
TOOL_DESCRIPTION = "在不同进制（二进制、十进制、十六进制）之间转换数字。"

class ToolWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self._is_updating = False  # Flag to prevent recursive updates

        # --- Widgets ---
        self.dec_input = QLineEdit()
        self.hex_input = QLineEdit()
        self.bin_input = QLineEdit()

        # --- Layout ---
        form_layout = QFormLayout()
        form_layout.addRow("十进制 (Decimal):", self.dec_input)
        form_layout.addRow("十六进制 (Hex):", self.hex_input)
        form_layout.addRow("二进制 (Binary):", self.bin_input)
        self.layout().addLayout(form_layout)

        # --- Signals ---
        self.dec_input.textChanged.connect(self.dec_changed)
        self.hex_input.textChanged.connect(self.hex_changed)
        self.bin_input.textChanged.connect(self.bin_changed)

    def dec_changed(self, text):
        if self._is_updating:
            return
        self._is_updating = True
        try:
            value = int(text)
            self.hex_input.setText(hex(value)[2:].upper())
            self.bin_input.setText(bin(value)[2:])
        except ValueError:
            self.hex_input.clear()
            self.bin_input.clear()
        self._is_updating = False

    def hex_changed(self, text):
        if self._is_updating:
            return
        self._is_updating = True
        try:
            value = int(text, 16)
            self.dec_input.setText(str(value))
            self.bin_input.setText(bin(value)[2:])
        except ValueError:
            self.dec_input.clear()
            self.bin_input.clear()
        self._is_updating = False

    def bin_changed(self, text):
        if self._is_updating:
            return
        self._is_updating = True
        try:
            value = int(text, 2)
            self.dec_input.setText(str(value))
            self.hex_input.setText(hex(value)[2:].upper())
        except ValueError:
            self.dec_input.clear()
            self.hex_input.clear()
        self._is_updating = False
