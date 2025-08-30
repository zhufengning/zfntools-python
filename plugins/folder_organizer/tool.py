import os
import json
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTextEdit,
    QMessageBox
)
from plugin_system import PluginType, WidgetPlugin

TOOL_NAME = "文件夹整理工具"
TOOL_DESCRIPTION = "将文件夹中的文件按照文件类型移动到不同的文件夹。"
PLUGIN_TYPE = PluginType.WIDGET

DEFAULT_CLASSIFICATION_MAP = {
    "图片": ["jpg", "png", "gif", "bmp", "jpeg", "svg", "webp"],
    "文档": ["doc", "docx", "pdf", "txt", "xls", "xlsx", "ppt", "pptx"],
    "视频": ["mp4", "avi", "mkv", "mov", "wmv"],
    "音频": ["mp3", "wav", "flac", "aac"],
    "压缩包": ["zip", "rar", "7z", "tar", "gz"],
    "代码": ["py", "js", "html", "css", "java", "c", "cpp", "go", "json", "xml"],
    "其他": []
}

class FolderOrganizerWidget(QWidget):
    def __init__(self, plugin_instance):
        super().__init__()
        self.plugin = plugin_instance
        self.data_dir = self.plugin.get_data_dir()
        self.config_path = os.path.join(self.data_dir, "config.json")
        self.classification_map = self.load_classification_map()
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.path_label = QLabel("请选择要整理的文件夹：")
        layout.addWidget(self.path_label)
        
        self.select_folder_button = QPushButton("选择文件夹")
        self.select_folder_button.clicked.connect(self.select_folder)
        layout.addWidget(self.select_folder_button)
        
        self.map_editor_label = QLabel("文件分类规则 (JSON格式):")
        layout.addWidget(self.map_editor_label)
        
        self.map_editor = QTextEdit()
        self.map_editor.setText(json.dumps(self.classification_map, indent=4, ensure_ascii=False))
        layout.addWidget(self.map_editor)
        
        self.save_map_button = QPushButton("保存规则")
        self.save_map_button.clicked.connect(self.save_classification_map)
        layout.addWidget(self.save_map_button)
        
        self.organize_button = QPushButton("开始整理")
        self.organize_button.clicked.connect(self.organize_folder)
        layout.addWidget(self.organize_button)
        
        self.selected_folder = ""

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.selected_folder = folder
            self.path_label.setText(f"已选择文件夹: {self.selected_folder}")

    def load_classification_map(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CLASSIFICATION_MAP, f, indent=4, ensure_ascii=False)
            return DEFAULT_CLASSIFICATION_MAP

    def save_classification_map(self):
        try:
            new_map = json.loads(self.map_editor.toPlainText())
            self.classification_map = new_map
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.classification_map, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "成功", "分类规则已保存。")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "错误", "JSON格式无效，请检查后重试。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存规则失败: {e}")

    def organize_folder(self):
        if not self.selected_folder:
            QMessageBox.warning(self, "提示", "请先选择一个文件夹。")
            return

        try:
            # Invert the map for faster lookup
            extension_map = {ext: category for category, exts in self.classification_map.items() for ext in exts}
            
            other_category = "其他"
            if other_category not in self.classification_map:
                other_category = next(iter(self.classification_map.keys())) if self.classification_map else "其他"


            for item in os.listdir(self.selected_folder):
                item_path = os.path.join(self.selected_folder, item)
                if os.path.isfile(item_path):
                    file_ext = item.split('.')[-1].lower() if '.' in item else ''
                    category = extension_map.get(file_ext, other_category)
                    
                    category_folder = os.path.join(self.selected_folder, category)
                    if not os.path.exists(category_folder):
                        os.makedirs(category_folder)
                        
                    shutil.move(item_path, os.path.join(category_folder, item))
            
            QMessageBox.information(self, "完成", "文件夹整理完毕！")

        except Exception as e:
            QMessageBox.critical(self, "整理失败", f"整理过程中发生错误: {e}")


class FolderOrganizerPlugin(WidgetPlugin):
    def __init__(self, plugin_dir: str = ""):
        super().__init__(plugin_dir)

    def get_name(self):
        return TOOL_NAME

    def get_description(self):
        return TOOL_DESCRIPTION

    def get_type(self):
        return PLUGIN_TYPE

    def create_widget(self):
        return FolderOrganizerWidget(self)