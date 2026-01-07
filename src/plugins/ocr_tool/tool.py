
import os
import io
import threading
import tempfile
import time
import sys
import json
import base64

# Monkey patch sys.stdout/stderr to avoid errors in no-console mode (pyinstaller --noconsole)
# doclayout_yolo checks sys.stdout.encoding which fails if sys.stdout is None
if sys.stdout is None:
    class DummyStream:
        encoding = 'utf-8'
        def write(self, s): pass
        def flush(self): pass
    sys.stdout = DummyStream()
    sys.stderr = DummyStream()
from typing import Optional, Any, cast
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QFileDialog, QScrollArea, QSplitter, QApplication,
    QProgressBar, QMessageBox, QCheckBox, QComboBox, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QDragEnterEvent, QDropEvent, QIcon, QAction, QKeySequence, QShortcut, QWheelEvent
from PySide6.QtCore import Qt, Signal, QThread, Slot, QObject, QMimeData, QBuffer, QIODevice, QEvent

from plugin_system import PluginType, WidgetPlugin

import inspect
# Monkey patch inspect.getsource to avoid errors in frozen environment
# when libraries (like older pix2text/rapidocr versions) try to read source code
if not hasattr(inspect, '_original_getsource'):
    _original_getsource = inspect.getsource
    def _safe_getsource(obj):
        try:
            return _original_getsource(obj)
        except (OSError, IOError):
            return "pass" # Must return non-empty string to avoid IndexError in transformers logic (splitlines()[0])
    inspect.getsource = _safe_getsource


import traceback

RapidOCR: Any = None
Image: Any = None
Pix2Text: Any = None

try:
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    HAS_RAPIDOCR = True
except Exception as e:
    print("Error importing RapidOCR:")
    traceback.print_exc()
    HAS_RAPIDOCR = False

try:
    from pix2text import Pix2Text
    HAS_PIX2TEXT = True
except Exception as e:
    print("Error importing Pix2Text:")
    traceback.print_exc()
    HAS_PIX2TEXT = False
    
HAS_DEPENDENCIES = HAS_RAPIDOCR # Basic requirement

TOOL_NAME = "图片文字识别(OCR)"
TOOL_DESCRIPTION = "识别图片中的文字，支持 RapidOCR / Pix2Text / AI 模式"

DEFAULT_OCR_MODE = "text"

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_API = "responses"  # "responses" | "chat_completions"
DEFAULT_AI_PROMPT = "对于输入的图片，请直接输出其中的文字识别结果。使用markdown和latex语法。"


def _get_openai_config_path_in_dir(config_dir: str) -> str:
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "openai_ocr.json")


def _get_ocr_tool_config_path_in_dir(config_dir: str) -> str:
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "ocr_tool.json")


def load_ocr_tool_config(config_dir: str) -> dict:
    config_path = _get_ocr_tool_config_path_in_dir(config_dir)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return {"last_mode": DEFAULT_OCR_MODE}


def save_ocr_tool_config(config: dict, config_dir: str) -> None:
    config_path = _get_ocr_tool_config_path_in_dir(config_dir)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_openai_config(config_dir: str) -> dict:
    config_path = _get_openai_config_path_in_dir(config_dir)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return {
        "base_url": DEFAULT_OPENAI_BASE_URL,
        "api_key": "",
        "model": DEFAULT_OPENAI_MODEL,
        "api": DEFAULT_OPENAI_API,
        "prompt": DEFAULT_AI_PROMPT,
    }


def save_openai_config(config: dict, config_dir: str) -> None:
    config_path = _get_openai_config_path_in_dir(config_dir)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class OpenAiSettingsDialog(QDialog):
    def __init__(self, parent=None, config_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("OCR AI 设置")
        if not config_dir:
            raise ValueError("config_dir is required for OpenAiSettingsDialog")
        self.config_dir = config_dir

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText(DEFAULT_OPENAI_BASE_URL)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-... / 或你的网关 Key")

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(DEFAULT_OPENAI_MODEL)

        self.api_mode_combo = QComboBox()
        self.api_mode_combo.addItem("Responses API (推荐)", "responses")
        self.api_mode_combo.addItem("Chat Completions", "chat_completions")

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(DEFAULT_AI_PROMPT)
        self.prompt_input.setFixedHeight(120)

        form.addRow("Base URL", self.base_url_input)
        form.addRow("API Key", self.api_key_input)
        form.addRow("Model", self.model_input)
        form.addRow("API", self.api_mode_combo)
        form.addRow("Prompt", self.prompt_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_from_disk()

    def load_from_disk(self):
        cfg = load_openai_config(self.config_dir)
        self.base_url_input.setText(cfg.get("base_url", DEFAULT_OPENAI_BASE_URL) or "")
        self.api_key_input.setText(cfg.get("api_key", "") or "")
        self.model_input.setText(cfg.get("model", DEFAULT_OPENAI_MODEL) or "")

        api_mode = cfg.get("api", DEFAULT_OPENAI_API) or DEFAULT_OPENAI_API
        index = self.api_mode_combo.findData(api_mode)
        if index >= 0:
            self.api_mode_combo.setCurrentIndex(index)

        self.prompt_input.setPlainText(cfg.get("prompt", DEFAULT_AI_PROMPT) or "")

    def get_config(self) -> dict:
        base_url = self.base_url_input.text().strip() or DEFAULT_OPENAI_BASE_URL
        api_key = self.api_key_input.text().strip()
        model = self.model_input.text().strip() or DEFAULT_OPENAI_MODEL
        api_mode = self.api_mode_combo.currentData() or DEFAULT_OPENAI_API
        prompt = self.prompt_input.toPlainText().strip() or DEFAULT_AI_PROMPT

        return {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "api": api_mode,
            "prompt": prompt,
        }

class OCRWorker(QObject):
    """OCR工作线程"""

    finished = Signal(object)  # (result_text, elapse_time) or (error_msg, None)

    def __init__(self, image_path_or_bytes, mode: str = "text", ai_config: Optional[dict] = None):
        super().__init__()
        self.image_source = image_path_or_bytes
        self.mode = mode
        self.ai_config = ai_config or {}

    def run(self):
        try:
            if self.mode == "ai":
                text_output = self._run_ai_ocr()
                self.finished.emit((text_output, 0))
                return

            if not HAS_DEPENDENCIES:
                self.finished.emit((
                    "错误: 缺少依赖库 rapidocr-onnxruntime 或 Pillow。\n请确保已安装: uv add rapidocr-onnxruntime Pillow",
                    0,
                ))
                return

            if self.mode == "latex":
                if not HAS_PIX2TEXT:
                    self.finished.emit(("错误: 缺少 pix2text 库，无法使用 Pix2Text 模式。\n请运行: uv add pix2text", 0))
                    return

                if Pix2Text is None or Image is None:
                    self.finished.emit(("错误: Pix2Text/Pillow 未正确加载，无法使用 Pix2Text 模式。", 0))
                    return

                p2t = Pix2Text.from_config()

                source = self.image_source
                if isinstance(source, bytes):
                    source = Image.open(io.BytesIO(source))

                result = p2t.recognize(source)

                text_output = str(result)
            else:
                if RapidOCR is None:
                    self.finished.emit(("错误: RapidOCR 未正确加载，无法使用 RapidOCR 模式。", 0))
                    return

                engine = RapidOCR()
                result, _elapse = engine(self.image_source)

                if result:
                    texts = [line[1] for line in result]
                    text_output = "\n".join(texts)
                else:
                    text_output = "未识别到文字"

            self.finished.emit((text_output, 0))
        except Exception as e:
            import traceback

            self.finished.emit((f"识别出错: {str(e)}\n{traceback.format_exc()}", 0))

    def _run_ai_ocr(self) -> str:
        try:
            from openai import OpenAI
        except Exception:
            return "错误: 缺少 openai SDK。请运行: uv add openai"

        api_key = (self.ai_config.get("api_key") or "").strip()
        if not api_key:
            return "错误: 未配置 OpenAI API Key，请点击“AI设置”进行配置。"

        base_url = (self.ai_config.get("base_url") or DEFAULT_OPENAI_BASE_URL).strip()
        model = (self.ai_config.get("model") or DEFAULT_OPENAI_MODEL).strip()
        prompt = (self.ai_config.get("prompt") or DEFAULT_AI_PROMPT).strip()

        image_bytes = self.image_source
        if not isinstance(image_bytes, (bytes, bytearray)):
            try:
                with open(str(self.image_source), "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                return f"错误: 无法读取图片: {e}"

        data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")

        client = OpenAI(api_key=api_key, base_url=base_url)

        api_mode = (self.ai_config.get("api") or DEFAULT_OPENAI_API).strip() or DEFAULT_OPENAI_API

        if api_mode == "responses":
            if not hasattr(client, "responses"):
                return "错误: 当前 openai SDK 不支持 Responses API，请在设置中切换为 Chat Completions。"

            resp = client.responses.create(
                model=model,
                input=cast(Any, [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ]),
            )

            output_text = getattr(resp, "output_text", None)
            if output_text:
                return str(output_text).strip()

            return str(resp)

        # chat_completions
        resp = client.chat.completions.create(
            model=model,
            messages=cast(Any, [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ]),
        )

        try:
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return str(resp)

class ToolWidget(QWidget):
    def __init__(self, plugin_instance):
        super().__init__()
        self.plugin = plugin_instance
        self.data_dir = self.plugin.get_data_dir()
        self.worker_thread = None
        self.setup_ui()
        self.ocr_engine = None
        self.current_image_path = None
        self.temp_file = None
        self.scale_factor = 1.0
        self.original_pixmap = None
        
        # Enable dropping files
        self.setAcceptDrops(True)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.btn_select = QPushButton("选择图片")
        self.btn_select.clicked.connect(self.select_image)
        
        self.btn_paste = QPushButton("粘贴图片 (Clipboard)")
        self.btn_paste.clicked.connect(self.paste_image)
        
        self.btn_recognize = QPushButton("开始识别")
        self.btn_recognize.clicked.connect(self.start_recognition)
        self.btn_recognize.setEnabled(False) # Diabled until image is loaded
        # Apply style to ensure visibility in dark mode and consistent look
        self.btn_recognize.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #808080;
                border: 1px solid #404040;
            }
        """)
        
        toolbar_layout.addWidget(self.btn_select)
        toolbar_layout.addWidget(self.btn_paste)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("RapidOCR 模式", "text")
        self.mode_combo.addItem("Pix2Text 模式", "latex")
        self.mode_combo.addItem("AI 模式", "ai")
        self.mode_combo.setToolTip("RapidOCR 模式: RapidOCR\nPix2Text 模式: Pix2Text\nAI 模式: OpenAI 视觉模型")
        self._restore_last_mode()
        self.mode_combo.currentIndexChanged.connect(self._persist_current_mode)
        toolbar_layout.addWidget(self.mode_combo)

        self.btn_ai_settings = QPushButton("AI设置")
        self.btn_ai_settings.setToolTip("配置 OpenAI Base URL / Key / Model / Prompt")
        self.btn_ai_settings.clicked.connect(self.open_ai_settings)
        toolbar_layout.addWidget(self.btn_ai_settings)

        toolbar_layout.addWidget(self.btn_recognize)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Warning if deps missing
        if not HAS_DEPENDENCIES:
            warning_label = QLabel("警告: 缺少 OCR 依赖库，请运行: uv add rapidocr-onnxruntime Pillow")
            warning_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(warning_label)
        
        # Main content (Splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Side Container (Zoom Controls + Image)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        # Zoom Controls
        zoom_layout = QHBoxLayout()
        self.btn_zoom_in = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.btn_reset_zoom = QPushButton("1:1")
        
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)
        
        # Style zoom buttons to be small/compact
        for btn in [self.btn_zoom_in, self.btn_zoom_out, self.btn_reset_zoom]:
            btn.setFixedWidth(50)
            btn.setStyleSheet("""
                QPushButton { padding: 3px; font-size: 11px; }
            """)
            
        zoom_layout.addWidget(self.btn_zoom_in)
        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_reset_zoom)
        zoom_layout.addStretch()
        
        left_layout.addLayout(zoom_layout)
        
        # Left: Image Preview
        self.image_container = QScrollArea()
        self.image_container.setWidgetResizable(False) # Important for zoom
        self.image_container.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center content
        self.image_container.setStyleSheet("QScrollArea { background-color: #e0e0e0; }") # Distinct background
        
        # Install event filter for wheel zoom
        self.image_container.viewport().installEventFilter(self)
        
        self.enable_drag_label = QLabel("请选择图片、粘贴图片\n或者将图片拖拽到此处")
        self.enable_drag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.enable_drag_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 2px dashed #ccc; color: #888; font-size: 14px; padding: 20px; }")
        
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.hide() # Initially hidden
        
        # We need a wrapper widget for scroll area to switch between label and preview
        self.preview_wrapper = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_wrapper)
        self.preview_layout.addWidget(self.enable_drag_label)
        self.preview_layout.addWidget(self.image_preview)
        self.preview_layout.setContentsMargins(0,0,0,0)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_container.setWidget(self.preview_wrapper)
        left_layout.addWidget(self.image_container)
        
        # Right: Result
        self.result_area = QTextEdit()
        self.result_area.setPlaceholderText("识别结果将显示在这里...")
        self.result_area.setReadOnly(False)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(self.result_area)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)
        
        # Status Bar / Progress
        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        
        status_layout = QHBoxLayout()
        # Create a container widget for status bar to enforce fixed height
        self.status_container = QWidget()
        self.status_container.setLayout(status_layout)
        self.status_container.setFixedHeight(40) # Fix height to avoid expanding
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        
        layout.addWidget(self.status_container)

        # Shortcuts
        self.paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_image)

    def eventFilter(self, source, event: QEvent):
        """Handle wheel event for zoom"""
        if source == self.image_container.viewport() and event.type() == QEvent.Type.Wheel:
            wheel_event = cast(QWheelEvent, event)
            if wheel_event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.handle_wheel_zoom(wheel_event)
                return True
        return super().eventFilter(source, event)

    def handle_wheel_zoom(self, event: QWheelEvent):
        angle = event.angleDelta().y()
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        if not self.original_pixmap: return
        self.scale_factor *= 1.1
        self.update_image_display()

    def zoom_out(self):
        if not self.original_pixmap: return
        self.scale_factor /= 1.1
        self.update_image_display()

    def reset_zoom(self):
        if not self.original_pixmap: return
        self.scale_factor = 1.0
        self.update_image_display()

    def update_image_display(self):
        if not self.original_pixmap:
            return
            
        new_size = self.original_pixmap.size() * self.scale_factor
        
        # Limit max/min zoom?
        
        new_pixmap = self.original_pixmap.scaled(
            new_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_preview.setPixmap(new_pixmap)
        self.image_preview.adjustSize()
        self.preview_wrapper.adjustSize()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self._is_image(file_path):
                    self.load_image(file_path)
        elif mime_data.hasImage():
            image = mime_data.imageData() # qvariant (qimage)
            self._process_qimage(image)
            
        event.acceptProposedAction()

    def _is_image(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        return ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if file_path:
            self.load_image(file_path)

    def paste_image(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                self._process_qimage(image)
        elif mime_data.hasUrls():
            # Copied file
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self._is_image(file_path):
                    self.load_image(file_path)

    def _process_qimage(self, qimage):
        """处理QImage对象"""
        self.current_image_path = None # Not a file path
        
        # Display
        pixmap = QPixmap.fromImage(qimage)
        self._display_pixmap(pixmap)
        
        # Save to temp file for OCR (reliable way for RapidOCR usually, or bytes)
        # Using bytes is better to avoid IO, but RapidOCR needs bytes passed carefully
        self._prepare_image_for_ocr(qimage)

    def load_image(self, file_path):
        self.current_image_path = file_path
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self._display_pixmap(pixmap)
            self.btn_recognize.setEnabled(True)
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
        else:
            QMessageBox.warning(self, "错误", "无法加载图片")

    def _display_pixmap(self, pixmap):
        # Resize if too large for preview? No, let ScrollArea handle it, or scale down for display
        # But for OCR we need full res.
        
        self.enable_drag_label.hide()
        self.image_preview.show()
        
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        
        # If image is very large, maybe default to "fit width" scale?
        # For now defaults to 1:1
        if pixmap.width() > self.image_container.width():
             self.scale_factor = (self.image_container.width() - 20) / pixmap.width()
             
        self.update_image_display()
        self.btn_recognize.setEnabled(True)

    def _prepare_image_for_ocr(self, qimage):
        """Save QImage to a format suitable for OCR (bytes or temp file)"""
        # Save to a temporary buffer
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        qimage.save(buffer, "PNG")
        self.current_image_bytes = buffer.data().data() # Convert QByteArray to bytes
        self.status_label.setText("图片已就绪 (来自剪贴板/拖拽)")

    def open_ai_settings(self):
        dialog = OpenAiSettingsDialog(self, config_dir=self.data_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cfg = dialog.get_config()
            save_openai_config(cfg, self.data_dir)

    def start_recognition(self):
        mode = "text"
        if hasattr(self, "mode_combo"):
            mode = self.mode_combo.currentData() or DEFAULT_OCR_MODE

        ai_config = None
        if mode == "ai":
            ai_config = load_openai_config(self.data_dir)
            if not (ai_config.get("api_key") or "").strip():
                QMessageBox.information(self, "AI模式", "请先配置 OpenAI Key / Model")
                self.open_ai_settings()
                ai_config = load_openai_config(self.data_dir)
                if not (ai_config.get("api_key") or "").strip():
                    return
        else:
            if not HAS_DEPENDENCIES:
                QMessageBox.critical(self, "错误", "缺少 rapidocr-onnxruntime 或 Pillow（RapidOCR/Pix2Text 模式需要）")
                return

        self.btn_recognize.setEnabled(False)
        self.progress_bar.setVisible(True)
        mode_label = self.mode_combo.currentText() if hasattr(self, "mode_combo") else mode
        self.status_label.setText(f"正在识别... ({mode_label})")
        self.result_area.clear()

        # Prepare bytes source for all modes
        source_bytes = None
        if self.current_image_path:
            try:
                with open(self.current_image_path, "rb") as f:
                    source_bytes = f.read()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取图片文件: {e}")
                self.progress_bar.setVisible(False)
                self.btn_recognize.setEnabled(True)
                return
        elif hasattr(self, "current_image_bytes"):
            source_bytes = self.current_image_bytes
        else:
            self.progress_bar.setVisible(False)
            self.btn_recognize.setEnabled(True)
            return

        # Start Thread
        self.worker_thread = QThread()
        self.worker = OCRWorker(source_bytes, mode, ai_config)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_recognition_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_recognition_finished(self, result):
        text, elapse = result
        
        self.progress_bar.setVisible(False)
        self.btn_recognize.setEnabled(True)
        self.status_label.setText("识别完成")
        
        self.result_area.setText(text)

    def _restore_last_mode(self) -> None:
        if not hasattr(self, "mode_combo"):
            return

        cfg = load_ocr_tool_config(self.data_dir)
        last_mode = cfg.get("last_mode", DEFAULT_OCR_MODE)
        index = self.mode_combo.findData(last_mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)

    def _persist_current_mode(self, _index: int) -> None:
        if not hasattr(self, "mode_combo"):
            return

        mode = self.mode_combo.currentData() or DEFAULT_OCR_MODE
        save_ocr_tool_config({"last_mode": mode}, self.data_dir)

class OCRPlugin(WidgetPlugin):
    def __init__(self, plugin_dir: str = ""):
        super().__init__(plugin_dir)

    def get_name(self) -> str:
        return TOOL_NAME
    
    def get_description(self) -> str:
        return TOOL_DESCRIPTION
    
    def get_type(self) -> PluginType:
        return PluginType.WIDGET
    
    def create_widget(self) -> QWidget:
        return ToolWidget(self)
