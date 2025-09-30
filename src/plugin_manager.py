# plugin_manager.py
import os
from PySide6.QtWidgets import QTabWidget, QMessageBox
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from plugin_system import (
    PluginLoader, BasePlugin, WidgetPlugin, 
    ActionPlugin, SearchPlugin, WebPlugin, SearchResult
)
from typing import List


class PluginManager:
    """插件管理器，负责加载和执行插件"""
    
    def __init__(self, plugins_dir: str, tab_widget: QTabWidget, parent):
        """
        初始化插件管理器
        
        Args:
            plugins_dir: 插件目录路径
            tab_widget: 标签页控件
            parent: 父窗口对象
        """
        self.plugins_dir = plugins_dir
        self.tab_widget = tab_widget
        self.parent = parent
        self.plugins = []
        
        # 加载插件
        self.load_plugins()
    
    def load_plugins(self) -> List[BasePlugin]:
        """加载所有插件"""
        self.plugins = PluginLoader.load_plugins(self.plugins_dir)
        return self.plugins
    
    def get_plugins(self) -> List[BasePlugin]:
        """获取所有插件"""
        return self.plugins
    
    def open_plugin(self, plugin: BasePlugin):
        """打开插件"""
        try:
            if isinstance(plugin, WidgetPlugin):
                self._open_widget_plugin(plugin)
            elif isinstance(plugin, ActionPlugin):
                self._execute_action_plugin(plugin)
            elif isinstance(plugin, WebPlugin):
                self._open_web_plugin(plugin)
            else:
                QMessageBox.warning(self.parent, "错误", f"不支持的插件类型: {plugin.get_type()}")
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"无法打开插件 '{plugin.get_name()}': {e}")
    
    def _open_widget_plugin(self, plugin: WidgetPlugin):
        """打开界面插件"""
        widget = plugin.create_widget()
        tab_name = plugin.get_name()
        
        # 确保标签名唯一
        new_tab_name = self._get_unique_tab_name(tab_name)
        
        index = self.tab_widget.addTab(widget, new_tab_name)
        self.tab_widget.setCurrentIndex(index)
    
    def _execute_action_plugin(self, plugin: ActionPlugin):
        """执行无界面插件"""
        reply = QMessageBox.question(
            self.parent, 
            "确认执行", 
            f"确定要执行 '{plugin.get_name()}' 吗？\n\n{plugin.get_description()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                plugin.execute()
                QMessageBox.information(self.parent, "成功", f"'{plugin.get_name()}' 执行完成")
            except Exception as e:
                QMessageBox.critical(self.parent, "执行失败", f"执行 '{plugin.get_name()}' 时出错: {e}")
    
    def _open_web_plugin(self, plugin: WebPlugin):
        """打开Web插件"""
        web_view = QWebEngineView()
        entry_path = plugin.get_entry_path()
        
        if os.path.exists(entry_path):
            url = QUrl.fromLocalFile(os.path.abspath(entry_path))
            web_view.load(url)
            
            tab_name = plugin.get_name()
            new_tab_name = self._get_unique_tab_name(tab_name)
            
            index = self.tab_widget.addTab(web_view, new_tab_name)
            self.tab_widget.setCurrentIndex(index)
        else:
            QMessageBox.critical(self.parent, "错误", f"找不到Web插件入口文件: {entry_path}")
    
    def _get_unique_tab_name(self, base_name: str) -> str:
        """获取唯一的标签名"""
        open_tabs = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        count = 1
        new_tab_name = base_name
        while new_tab_name in open_tabs:
            count += 1
            new_tab_name = f"{base_name} ({count})"
        return new_tab_name
    
    def execute_search_result(self, result: SearchResult, search_plugin: SearchPlugin):
        """执行搜索结果"""
        try:
            search_plugin.execute_result(result)
            self.parent.hide()
        except Exception as e:
            QMessageBox.critical(self.parent, "执行失败", f"执行搜索结果时出错: {e}")
