
import os
import io
import threading
import tempfile
import time
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QFileDialog, QScrollArea, QSplitter, QApplication,
    QProgressBar, QMessageBox, QCheckBox
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QDragEnterEvent, QDropEvent, QIcon, QAction, QKeySequence, QShortcut, QWheelEvent
from PySide6.QtCore import Qt, Signal, QThread, Slot, QObject, QMimeData, QBuffer, QIODevice, QEvent

from plugin_system import PluginType, WidgetPlugin

# Try importing dependencies
try:
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    HAS_RAPIDOCR = True
except ImportError:
    HAS_RAPIDOCR = False

try:
    from pix2text import Pix2Text
    HAS_PIX2TEXT = True
except ImportError:
    HAS_PIX2TEXT = False
    
HAS_DEPENDENCIES = HAS_RAPIDOCR # Basic requirement

TOOL_NAME = "图片文字识别(OCR)"
TOOL_DESCRIPTION = "识别图片中的文字，支持latex模式"

class OCRWorker(QObject):
    """OCR工作线程"""
    finished = Signal(object) # (result_text, elapse_time) or (error_msg, None)
    
    def __init__(self, image_path_or_bytes, mode='text'):
        super().__init__()
        self.image_source = image_path_or_bytes
        self.mode = mode
        
    def run(self):
        try:
            if not HAS_DEPENDENCIES:
                self.finished.emit(("错误: 缺少依赖库 rapidocr-onnxruntime 或 Pillow。\n请确保已安装: uv add rapidocr-onnxruntime Pillow", 0))
                return

            # Initialize engine (can be slow, maybe better to initialize once globally or in main thread if thread-safe? 
            # RapidOCR instances are lightweight but loading models takes time. 
            # Ideally we keep one instance, but for simplicity let's create here for now or optimize later.)
            # To catch init errors early:
            # Run OCR
            if self.mode == 'latex':
                if not HAS_PIX2TEXT:
                     self.finished.emit(("错误: 缺少 pix2text 库，无法使用 LaTeX 模式。\n请运行: uv add pix2text", 0))
                     return
                
                # Initialize Pix2Text
                # It might be slow on first run to download models
                p2t = Pix2Text.from_config()
                # recognize_text method handles both text and formula? actually .recognize() is the main entry
                # usage: p2t.recognize(img, resized_shape=608, return_text=True)
                # It accepts path or PIL Image or numpy array
                
                # Convert bytes to PIL Image if needed, or pass path
                source = self.image_source
                if isinstance(source, bytes):
                    source = Image.open(io.BytesIO(source))
                
                # Pix2Text recognize returns text directly if return_text=True? 
                # Or dict? Check docs. standard is: 
                # out = p2t.recognize(img) -> returns str (if simple) or detailed dict
                # Actually usage: 
                # outs = img_ocr.recognize(img_path) 
                # print(outs)
                
                # Let's try simple call
                result = p2t.recognize(source) # Returns str usually for mixed content
                text_output = str(result)
                
            else:
                # Text Mode (RapidOCR)
                engine = RapidOCR()
                result, elapse = engine(self.image_source)
                
                text_output = ""
                if result:
                    texts = [line[1] for line in result]
                    text_output = "\n".join(texts)
                else:
                    text_output = "未识别到文字"
                
            self.finished.emit((text_output, 0))
            
        except Exception as e:
            import traceback
            self.finished.emit((f"识别出错: {str(e)}\n{traceback.format_exc()}", 0))

class ToolWidget(QWidget):
    def __init__(self):
        super().__init__()
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
        
        # LaTeX Checkbox
        self.chk_latex = QCheckBox("LaTeX 公式模式")
        self.chk_latex.setToolTip("开启后使用 Pix2Text 识别数学公式")
        toolbar_layout.addWidget(self.chk_latex)
        
        toolbar_layout.addWidget(self.btn_recognize)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Warning if deps missing
        if not HAS_DEPENDENCIES:
            warning_label = QLabel("警告: 缺少 OCR 依赖库，请运行: uv add rapidocr-onnxruntime Pillow")
            warning_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(warning_label)
        
        # Main content (Splitter)
        splitter = QSplitter(Qt.Horizontal)
        
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
        self.image_container.setAlignment(Qt.AlignCenter) # Center content
        self.image_container.setStyleSheet("QScrollArea { background-color: #e0e0e0; }") # Distinct background
        
        # Install event filter for wheel zoom
        self.image_container.viewport().installEventFilter(self)
        
        self.enable_drag_label = QLabel("请选择图片、粘贴图片\n或者将图片拖拽到此处")
        self.enable_drag_label.setAlignment(Qt.AlignCenter)
        self.enable_drag_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 2px dashed #ccc; color: #888; font-size: 14px; padding: 20px; }")
        
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide() # Initially hidden
        
        # We need a wrapper widget for scroll area to switch between label and preview
        self.preview_wrapper = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_wrapper)
        self.preview_layout.addWidget(self.enable_drag_label)
        self.preview_layout.addWidget(self.image_preview)
        self.preview_layout.setContentsMargins(0,0,0,0)
        self.preview_layout.setAlignment(Qt.AlignCenter)
        
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
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_image)

    def eventFilter(self, source, event: QEvent):
        """Handle wheel event for zoom"""
        if source == self.image_container.viewport() and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                self.handle_wheel_zoom(event)
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
        
        new_pixmap = self.original_pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        buffer.open(QIODevice.ReadWrite)
        qimage.save(buffer, "PNG")
        self.current_image_bytes = buffer.data().data() # Convert QByteArray to bytes
        self.status_label.setText("图片已就绪 (来自剪贴板/拖拽)")

    def start_recognition(self):
        if not HAS_DEPENDENCIES:
             QMessageBox.critical(self, "错误", "缺少 rapidocr-onnxruntime 库")
             return

        self.btn_recognize.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在识别...（首次使用Latex模式时会自动下载模型）")
        self.result_area.clear()
        
        # Prepare source
        source = None
        if self.current_image_path:
            source = self.current_image_path
        elif hasattr(self, 'current_image_bytes'):
            source = self.current_image_bytes
        else:
            # Should not happen
            return

        # Start Thread
        mode = 'latex' if self.chk_latex.isChecked() else 'text'
        self.thread = QThread()
        self.worker = OCRWorker(source, mode)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_recognition_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    def on_recognition_finished(self, result):
        text, elapse = result
        
        self.progress_bar.setVisible(False)
        self.btn_recognize.setEnabled(True)
        self.status_label.setText("识别完成")
        
        self.result_area.setText(text)

class OCRPlugin(WidgetPlugin):
    def get_name(self) -> str:
        return TOOL_NAME
    
    def get_description(self) -> str:
        return TOOL_DESCRIPTION
    
    def get_type(self) -> PluginType:
        return PluginType.WIDGET
    
    def create_widget(self) -> QWidget:
        return ToolWidget()
