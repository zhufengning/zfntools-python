# plugins/color_picker/tool.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QColorDialog, QPushButton, QLabel, QHBoxLayout
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtCore import Qt

TOOL_NAME = "颜色选择器"
TOOL_DESCRIPTION = "从调色板中选择颜色并获取其不同格式的值。"

class ToolWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)

        self.color = QColor("#FFFFFF")

        # --- Widgets ---
        self.color_preview = QLabel("Selected Color")
        self.color_preview.setAutoFillBackground(True)
        self.color_preview.setAlignment(Qt.AlignCenter)
        self.color_preview.setMinimumHeight(100)
        font = self.color_preview.font()
        font.setPointSize(15)
        self.color_preview.setFont(font)


        self.pick_button = QPushButton("选择颜色")
        self.hex_label = QLabel()
        self.rgb_label = QLabel()
        self.hsl_label = QLabel()

        # --- Layout ---
        self.layout().addWidget(self.pick_button)
        self.layout().addWidget(self.color_preview)
        self.layout().addWidget(self.hex_label)
        self.layout().addWidget(self.rgb_label)
        self.layout().addWidget(self.hsl_label)


        # --- Signals ---
        self.pick_button.clicked.connect(self.pick_color)

        # --- Initial State ---
        self.update_color(QColor("#007BFF"))


    def pick_color(self):
        color = QColorDialog.getColor(self.color, self, "Select Color")
        if color.isValid():
            self.update_color(color)

    def update_color(self, color):
        self.color = color

        # Update preview background
        palette = self.color_preview.palette()
        palette.setColor(QPalette.Window, self.color)
        self.color_preview.setPalette(palette)

        # Update preview text color for contrast
        r, g, b, _ = color.getRgb()
        # Simple brightness check
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            text_color = QColor(Qt.black)
        else:
            text_color = QColor(Qt.white)

        text_palette = self.color_preview.palette()
        text_palette.setColor(QPalette.WindowText, text_color)
        self.color_preview.setPalette(text_palette)


        # Update labels
        hex_code = self.color.name().upper()
        self.color_preview.setText(hex_code)
        self.hex_label.setText(f"<b>HEX:</b> {hex_code}")
        self.rgb_label.setText(f"<b>RGB:</b> {color.red()}, {color.green()}, {color.blue()}")
        self.hsl_label.setText(f"<b>HSL:</b> {color.hslHue()}, {color.hslSaturation()}, {color.lightness()}")
