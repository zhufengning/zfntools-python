# main.py
import sys
import os
import importlib.util
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QLabel, QHBoxLayout,
    QFrame, QTabBar, QMessageBox
)
from PySide6.QtGui import QIcon, Qt
from PySide6.QtCore import QSize, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from plugin_system import PluginLoader, PluginType, BasePlugin, WidgetPlugin, ActionPlugin, SearchPlugin, WebPlugin, SearchResult

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 工具箱")
        self.setGeometry(100, 100, 900, 600)

        # 加载所有插件
        self.plugins = self.load_plugins()
        self.search_plugins = [p for p in self.plugins if isinstance(p, SearchPlugin)]

        # --- Main Tab Widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # --- Home Tab (Tool List) ---
        self.home_tab = QWidget()
        self.setup_home_tab()
        self.tab_widget.addTab(self.home_tab, "首页")
        # Remove the close button on the home tab
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        self.update_tool_list()

    def load_plugins(self):
        """加载所有插件"""
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        return PluginLoader.load_plugins(plugins_dir)

    def setup_home_tab(self):
        """Sets up the layout and widgets for the home tab."""
        layout = QVBoxLayout(self.home_tab)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索工具和应用程序...")
        self.search_bar.textChanged.connect(self.perform_search)
        layout.addWidget(self.search_bar)

        # Tool list
        self.tool_list_widget = QListWidget()
        self.tool_list_widget.itemDoubleClicked.connect(self.handle_item_activation)
        self.tool_list_widget.setWordWrap(True)
        layout.addWidget(self.tool_list_widget)

    def update_tool_list(self):
        """显示所有已加载的插件"""
        self.tool_list_widget.clear()
        for plugin in self.plugins:
            self._add_plugin_to_list(plugin, is_search_result=False)
    
    def _add_plugin_to_list(self, plugin: BasePlugin, is_search_result: bool = False, search_result: SearchResult = None):
        """将插件添加到列表中"""
        item = QListWidgetItem()
        
        # Create a custom widget for the list item
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        if is_search_result and search_result:
            name_label = QLabel(f"<b>{search_result.title}</b>")
            desc_label = QLabel(f"<small>{search_result.description}</small>")
            plugin_label = QLabel(f"<i>来自: {search_result.plugin_name}</i>")
            plugin_label.setStyleSheet("color: #666;")
            
            layout.addWidget(name_label)
            layout.addWidget(desc_label)
            layout.addWidget(plugin_label)
            
            # Store search result data
            item.setData(Qt.UserRole, {'type': 'search_result', 'result': search_result, 'plugin': plugin})
        else:
            name_label = QLabel(f"<b>{plugin.get_name()}</b>")
            desc_label = QLabel(f"<small>{plugin.get_description()}</small>")
            type_label = QLabel(f"<i>类型: {self._get_plugin_type_display(plugin.get_type())}</i>")
            type_label.setStyleSheet("color: #666;")
            
            layout.addWidget(name_label)
            layout.addWidget(desc_label)
            layout.addWidget(type_label)
            
            # Store plugin data
            item.setData(Qt.UserRole, {'type': 'plugin', 'plugin': plugin})
        
        desc_label.setWordWrap(True)
        
        item.setSizeHint(widget.sizeHint())
        self.tool_list_widget.addItem(item)
        self.tool_list_widget.setItemWidget(item, widget)
    
    def _get_plugin_type_display(self, plugin_type: PluginType) -> str:
        """获取插件类型的显示名称"""
        type_map = {
            PluginType.WIDGET: "界面工具",
            PluginType.ACTION: "快捷操作",
            PluginType.SEARCH: "搜索工具",
            PluginType.WEB: "Web应用"
        }
        return type_map.get(plugin_type, "未知类型")


    def perform_search(self, text: str):
        """执行搜索，包括插件过滤和搜索插件结果"""
        self.tool_list_widget.clear()
        text_lower = text.lower().strip()
        
        if not text_lower:
            # 如果搜索框为空，显示所有插件
            self.update_tool_list()
            return
        
        # 过滤本地插件
        for plugin in self.plugins:
            if (text_lower in plugin.get_name().lower() or 
                text_lower in plugin.get_description().lower()):
                self._add_plugin_to_list(plugin, is_search_result=False)
        
        # 调用搜索插件
        for search_plugin in self.search_plugins:
            try:
                results = search_plugin.search(text)
                for result in results:
                    self._add_plugin_to_list(search_plugin, is_search_result=True, search_result=result)
            except Exception as e:
                print(f"搜索插件 '{search_plugin.get_name()}' 出错: {e}")
    
    def handle_item_activation(self, item):
        """处理项目激活（双击）"""
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'plugin':
            self.open_plugin(data['plugin'])
        elif data['type'] == 'search_result':
            self.execute_search_result(data['result'], data['plugin'])

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
                QMessageBox.warning(self, "错误", f"不支持的插件类型: {plugin.get_type()}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开插件 '{plugin.get_name()}': {e}")
    
    def _open_widget_plugin(self, plugin: WidgetPlugin):
        """打开界面插件"""
        widget = plugin.create_widget()
        tab_name = plugin.get_name()
        
        # Check if this tool is already open, if so, add a number
        open_tabs = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        count = 1
        new_tab_name = tab_name
        while new_tab_name in open_tabs:
            count += 1
            new_tab_name = f"{tab_name} ({count})"

        index = self.tab_widget.addTab(widget, new_tab_name)
        self.tab_widget.setCurrentIndex(index)
    
    def _execute_action_plugin(self, plugin: ActionPlugin):
        """执行无界面插件"""
        reply = QMessageBox.question(
            self, 
            "确认执行", 
            f"确定要执行 '{plugin.get_name()}' 吗？\n\n{plugin.get_description()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                plugin.execute()
                QMessageBox.information(self, "成功", f"'{plugin.get_name()}' 执行完成")
            except Exception as e:
                QMessageBox.critical(self, "执行失败", f"执行 '{plugin.get_name()}' 时出错: {e}")
    
    def _open_web_plugin(self, plugin: WebPlugin):
        """打开Web插件"""
        web_view = QWebEngineView()
        entry_path = plugin.get_entry_path()
        
        if os.path.exists(entry_path):
            url = QUrl.fromLocalFile(os.path.abspath(entry_path))
            web_view.load(url)
            
            tab_name = plugin.get_name()
            
            # Check if this tool is already open, if so, add a number
            open_tabs = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
            count = 1
            new_tab_name = tab_name
            while new_tab_name in open_tabs:
                count += 1
                new_tab_name = f"{tab_name} ({count})"

            index = self.tab_widget.addTab(web_view, new_tab_name)
            self.tab_widget.setCurrentIndex(index)
        else:
            QMessageBox.critical(self, "错误", f"找不到Web插件入口文件: {entry_path}")
    
    def execute_search_result(self, result: SearchResult, search_plugin: SearchPlugin):
        """执行搜索结果"""
        try:
            search_plugin.execute_result(result)
        except Exception as e:
            QMessageBox.critical(self, "执行失败", f"执行搜索结果时出错: {e}")

    def close_tab(self, index):
        """Closes a tab."""
        # Do not close the home tab
        if self.tab_widget.widget(index) == self.home_tab:
            return
            
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
