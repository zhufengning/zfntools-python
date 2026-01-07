import json
import os
from typing import Optional

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from plugin_system import PluginType, WidgetPlugin

TOOL_NAME = "Markdown 预览"
TOOL_DESCRIPTION = "离线 Markdown 编辑/预览，支持 KaTeX 数学公式渲染。"
PLUGIN_TYPE = PluginType.WIDGET


class MarkdownPreviewWidget(QWidget):
    def __init__(self, plugin_instance):
        super().__init__()
        self.plugin = plugin_instance
        self.data_dir = self.plugin.get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_path = os.path.join(self.data_dir, "settings.json")

        self.current_file_path: Optional[str] = None
        self.current_md_base_url: str = "file:///"
        self.devtools_dialog: Optional[QDialog] = None
        self.devtools_page: Optional[QWebEnginePage] = None

        self._load_settings()
        self._setup_ui()
        self._setup_shortcuts()

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._render_preview)
        self.editor.textChanged.connect(self._schedule_render)

        if self.current_file_path and os.path.isfile(self.current_file_path):
            self._open_file(self.current_file_path)
        else:
            self._render_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_open = QPushButton("打开 .md")
        self.btn_save = QPushButton("保存")
        self.btn_save_as = QPushButton("另存为")
        self.btn_devtools = QPushButton("DevTools(F12)")
        self.btn_open.clicked.connect(self.open_file_dialog)
        self.btn_save.clicked.connect(self.save)
        self.btn_save_as.clicked.connect(self.save_as)
        self.btn_devtools.clicked.connect(self.toggle_devtools)

        self.path_label = QLabel("")
        self.path_label.setStyleSheet("color: #666;")

        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_save_as)
        toolbar.addWidget(self.btn_devtools)
        toolbar.addWidget(self.path_label, 1)
        layout.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("在这里输入 Markdown…（支持 $...$ 和 $$...$$）")

        self.preview = QWebEngineView()
        self.preview.setContextMenuPolicy(self.editor.contextMenuPolicy())

        splitter = QSplitter()
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.setAcceptDrops(True)

    def _setup_shortcuts(self) -> None:
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save)

        open_shortcut = QShortcut(QKeySequence.StandardKey.Open, self)
        open_shortcut.activated.connect(self.open_file_dialog)

        devtools_shortcut = QShortcut(QKeySequence("F12"), self)
        devtools_shortcut.activated.connect(self.toggle_devtools)

    def _load_settings(self) -> None:
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.current_file_path = data.get("last_file") or None
        except Exception:
            self.current_file_path = None

    def _save_settings(self) -> None:
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump({"last_file": self.current_file_path or ""}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "打开 Markdown 文件", "", "Markdown (*.md *.markdown);;All Files (*.*)")
        if path:
            self._open_file(path)

    def _open_file(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法读取文件:\n{e}")
            return

        self.current_file_path = path
        self._save_settings()

        self.path_label.setText(path)
        base_dir = os.path.dirname(os.path.abspath(path))
        if not base_dir.endswith(os.sep):
            base_dir += os.sep
        self.current_md_base_url = "file:///" + base_dir.replace("\\", "/")

        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self._render_preview()

    def save(self) -> None:
        if not self.current_file_path:
            self.save_as()
            return
        try:
            with open(self.current_file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.statusTip()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法写入文件:\n{e}")

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存 Markdown 文件", "", "Markdown (*.md *.markdown);;All Files (*.*)")
        if not path:
            return
        self.current_file_path = path
        self._save_settings()
        self.path_label.setText(path)
        self.save()

    def _schedule_render(self) -> None:
        self.render_timer.start(200)

    def _assets_exist(self) -> bool:
        plugin_dir = self.plugin.plugin_dir
        katex_js = os.path.join(plugin_dir, "assets", "katex", "katex.min.js")
        katex_css = os.path.join(plugin_dir, "assets", "katex", "katex.min.css")
        auto_render = os.path.join(plugin_dir, "assets", "katex", "contrib", "auto-render.min.js")
        marked_js = os.path.join(plugin_dir, "assets", "marked.min.js")
        return all(os.path.exists(p) for p in [katex_js, katex_css, auto_render, marked_js])

    def _render_preview(self) -> None:
        if not self._assets_exist():
            self.preview.setHtml(
                "<h3>缺少离线资源</h3>"
                "<p>未找到 KaTeX/marked 资源文件。请在插件目录下提供：</p>"
                "<ul>"
                "<li>assets/marked.min.js</li>"
                "<li>assets/katex/katex.min.js</li>"
                "<li>assets/katex/katex.min.css</li>"
                "<li>assets/katex/contrib/auto-render.min.js</li>"
                "<li>assets/katex/fonts/*.woff2</li>"
                "</ul>"
            )
            return

        md = self.editor.toPlainText()
        md_json = json.dumps(md, ensure_ascii=False)
        base_url_json = json.dumps(self.current_md_base_url, ensure_ascii=False)

        html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="assets/github-markdown.min.css" />
    <link rel="stylesheet" href="assets/katex/katex.min.css" />
    <style>
      body {{ margin: 0; padding: 12px 16px; }}
      .markdown-body {{ box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; }}
      img {{ max-width: 100%; }}
      pre {{ overflow: auto; }}
    </style>
  </head>
  <body class="markdown-body">
    <div id="content"></div>
    <script src="assets/marked.min.js"></script>
    <script src="assets/katex/katex.min.js"></script>
    <script src="assets/katex/contrib/auto-render.min.js"></script>
    <script>
      const mdBase = {base_url_json};
      const renderer = new marked.Renderer();
      const resolveUrl = (href) => {{
        if (!href) return href;
        try {{
          // keep anchors
          if (href.startsWith("#")) return href;
          return new URL(href, mdBase).toString();
        }} catch (e) {{
          return href;
        }}
      }};
      renderer.link = (href, title, text) => {{
        const resolved = resolveUrl(href);
        const t = title ? ` title="${{title}}"` : "";
        return `<a href="${{resolved}}"${{t}} target="_blank" rel="noreferrer noopener">${{text}}</a>`;
      }};
      renderer.image = (href, title, text) => {{
        const resolved = resolveUrl(href);
        const t = title ? ` title="${{title}}"` : "";
        const alt = text ? ` alt="${{text}}"` : ' alt=""';
        return `<img src="${{resolved}}"${{alt}}${{t}} />`;
      }};

      const content = document.getElementById("content");
      const md = {md_json};

      // Protect multiline $$...$$ blocks from being split by Markdown rendering (e.g. <br>),
      // then restore them as plain text so KaTeX auto-render can process them reliably.
      const mathBlocks = [];
      const mdWithPlaceholders = md.replace(/\\$\\$([\\s\\S]+?)\\$\\$/g, (full, inner) => {{
        const idx = mathBlocks.length;
        mathBlocks.push(inner);
        return `\\n\\n<span data-math-block="${{idx}}"></span>\\n\\n`;
      }});

      content.innerHTML = marked.parse(mdWithPlaceholders, {{
        breaks: true,
        gfm: true,
        renderer,
      }});

      document.querySelectorAll("[data-math-block]").forEach((el) => {{
        const idx = Number(el.getAttribute("data-math-block"));
        const inner = mathBlocks[idx] ?? "";
        el.textContent = `$$\\n${{inner}}\\n$$`;
      }});

      renderMathInElement(content, {{
        delimiters: [
          {{ left: "$$", right: "$$", display: true }},
          {{ left: "$", right: "$", display: false }},
        ],
        throwOnError: false,
      }});
    </script>
  </body>
</html>"""

        plugin_dir = os.path.abspath(self.plugin.plugin_dir)
        if not plugin_dir.endswith(os.sep):
            plugin_dir += os.sep
        self.preview.setHtml(html, QUrl.fromLocalFile(plugin_dir))

    def toggle_devtools(self) -> None:
        if self.devtools_dialog is not None:
            if self.devtools_dialog.isVisible():
                self.devtools_dialog.close()
                return
            self.devtools_dialog.show()
            self.devtools_dialog.raise_()
            self.devtools_dialog.activateWindow()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Markdown 预览 - DevTools")
        dialog.resize(1100, 700)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog_layout = QVBoxLayout(dialog)
        devtools_view = QWebEngineView(dialog)
        dialog_layout.addWidget(devtools_view)

        devtools_page = QWebEnginePage(self.preview.page().profile(), devtools_view)
        devtools_view.setPage(devtools_page)
        self.preview.page().setDevToolsPage(devtools_page)

        self.devtools_dialog = dialog
        self.devtools_page = devtools_page
        dialog.destroyed.connect(self._on_devtools_destroyed)
        dialog.show()

    def _on_devtools_destroyed(self) -> None:
        try:
            self.preview.page().setDevToolsPage(None)
        except Exception:
            pass
        self.devtools_dialog = None
        self.devtools_page = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path and os.path.isfile(path) and os.path.splitext(path)[1].lower() in {".md", ".markdown"}:
            self._open_file(path)


class MarkdownPreviewPlugin(WidgetPlugin):
    def __init__(self, plugin_dir: str = ""):
        super().__init__(plugin_dir)

    def get_name(self) -> str:
        return TOOL_NAME

    def get_description(self) -> str:
        return TOOL_DESCRIPTION

    def get_type(self) -> PluginType:
        return PLUGIN_TYPE

    def create_widget(self) -> QWidget:
        return MarkdownPreviewWidget(self)
