# main.py
import sys
import os
import importlib.util
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QLabel, QHBoxLayout,
    QFrame, QTabBar, QMessageBox
)
from PySide6.QtGui import QIcon, Qt, QKeyEvent
from PySide6.QtCore import QSize, QUrl, QThread, Signal, QObject, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from plugin_system import PluginLoader, PluginType, BasePlugin, WidgetPlugin, ActionPlugin, SearchPlugin, WebPlugin, SearchResult
from search_engine import SearchableItem, get_search_engine
from typing import List

class SearchWorker(QObject):
    """搜索工作线程"""
    results_ready = Signal(str, list)  # plugin_name, results
    finished = Signal(str)  # plugin_name
    
    def __init__(self, plugin: SearchPlugin, query: str):
        super().__init__()
        self.plugin = plugin
        self.query = query
        self.plugin_name = plugin.get_name()
    
    def run(self):
        """执行搜索"""
        try:
            results = self.plugin.search(self.query)
            self.results_ready.emit(self.plugin_name, results)
        except Exception as e:
            print(f"搜索插件 '{self.plugin_name}' 出错: {e}")
            self.results_ready.emit(self.plugin_name, [])
        finally:
            self.finished.emit(self.plugin_name)

class LocalSearchWorker(QObject):
    """本地插件搜索工作线程"""
    results_ready = Signal(list)  # local results
    finished = Signal()
    
    def __init__(self, query: str):
        super().__init__()
        self.query = query
    
    def run(self):
        """执行本地搜索"""
        try:
            search_engine = get_search_engine()
            local_results = search_engine.search(self.query, max_results=20)
            self.results_ready.emit(local_results)
        except Exception as e:
            print(f"本地搜索出错: {e}")
            self.results_ready.emit([])
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 工具箱")
        self.setGeometry(100, 100, 900, 600)

        # 加载所有插件
        self.plugins = self.load_plugins()
        self.search_plugins = [p for p in self.plugins if isinstance(p, SearchPlugin)]

        # 初始化搜索引擎
        self.setup_search_engine()
        
        # 异步搜索相关
        self.search_threads = []  # 存储搜索线程
        self.search_workers = []  # 存储搜索工作对象
        self.current_search_query = ""  # 当前搜索查询
        self.search_timer = QTimer()  # 搜索防抖定时器
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.start_async_search)
        self.pending_results = {}  # 存储待显示的结果

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

        # 启动时聚焦到搜索框
        self.search_bar.setFocus()

    def load_plugins(self):
        """加载所有插件"""
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        return PluginLoader.load_plugins(plugins_dir)
    
    def setup_search_engine(self):
        """设置搜索引擎并添加本地插件"""
        search_engine = get_search_engine()
        search_engine.clear()
        
        # 添加本地插件到搜索引擎
        for plugin in self.plugins:
            if not isinstance(plugin, SearchPlugin):  # 搜索插件本身不加入搜索
                item = SearchableItem(
                    title=plugin.get_name(),
                    description=plugin.get_description(),
                    data=plugin
                )
                search_engine.add_item(item)

    def setup_home_tab(self):
        """Sets up the layout and widgets for the home tab."""
        layout = QVBoxLayout(self.home_tab)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索工具和应用程序...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        self.search_bar.keyPressEvent = self.search_bar_key_press_event
        layout.addWidget(self.search_bar)

        # Tool list
        self.tool_list_widget = QListWidget()
        self.tool_list_widget.itemDoubleClicked.connect(self.handle_item_activation)
        self.tool_list_widget.setWordWrap(True)
        self.tool_list_widget.keyPressEvent = self.list_key_press_event
        layout.addWidget(self.tool_list_widget)

    def update_tool_list(self):
        """显示所有已加载的插件"""
        self.tool_list_widget.clear()
        for plugin in self.plugins:
            self._add_plugin_to_list(plugin, is_search_result=False)
    
    def search_bar_key_press_event(self, event: QKeyEvent):
        """搜索栏键盘事件处理"""
        if event.key() == Qt.Key_Down:
            # 下键：选择列表中的下一项，但保持搜索框焦点
            if self.tool_list_widget.count() > 0:
                current_row = self.tool_list_widget.currentRow()
                if current_row < 0:
                    # 如果没有选中项，选择第一项
                    self.tool_list_widget.setCurrentRow(0)
                elif current_row < self.tool_list_widget.count() - 1:
                    # 选择下一项
                    self.tool_list_widget.setCurrentRow(current_row + 1)
        elif event.key() == Qt.Key_Up:
            # 上键：选择列表中的上一项，但保持搜索框焦点
            if self.tool_list_widget.count() > 0:
                current_row = self.tool_list_widget.currentRow()
                if current_row < 0:
                    # 如果没有选中项，选择最后一项
                    self.tool_list_widget.setCurrentRow(self.tool_list_widget.count() - 1)
                elif current_row > 0:
                    # 选择上一项
                    self.tool_list_widget.setCurrentRow(current_row - 1)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 回车键：激活当前选中的项目
            if self.tool_list_widget.count() > 0:
                current_item = self.tool_list_widget.currentItem()
                if current_item:
                    self.handle_item_activation(current_item)
                else:
                    # 如果没有选中项，选择第一项并激活
                    self.tool_list_widget.setCurrentRow(0)
                    self.handle_item_activation(self.tool_list_widget.currentItem())
        else:
            # 其他键：调用原始的keyPressEvent
            QLineEdit.keyPressEvent(self.search_bar, event)
    
    def list_key_press_event(self, event: QKeyEvent):
        """列表键盘事件处理"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 回车键：激活当前选中的项目
            current_item = self.tool_list_widget.currentItem()
            if current_item:
                self.handle_item_activation(current_item)
        elif event.key() == Qt.Key_Escape:
            # ESC键：将焦点返回到搜索栏
            self.search_bar.setFocus()
        else:
            # 其他键：调用原始的keyPressEvent（包括上下键导航）
            QListWidget.keyPressEvent(self.tool_list_widget, event)
    
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


    def on_search_text_changed(self, text: str):
        """搜索文本变化时的处理（防抖）"""
        self.current_search_query = text.strip()
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms防抖延迟
    
    def start_async_search(self):
        """开始异步搜索"""
        # 停止所有正在进行的搜索
        self.stop_all_searches()
        
        query = self.current_search_query
        if not query:
            # 如果搜索框为空，显示所有插件
            self.update_tool_list()
            return
        
        # 清空结果列表
        self.tool_list_widget.clear()
        self.pending_results = {}
        
        # 启动本地搜索
        self.start_local_search(query)
        
        # 启动搜索插件搜索
        for search_plugin in self.search_plugins:
            self.start_plugin_search(search_plugin, query)
    
    def start_local_search(self, query: str):
        """启动本地插件搜索"""
        thread = QThread()
        worker = LocalSearchWorker(query)
        
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self.on_local_results_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self.search_threads.append(thread)
        self.search_workers.append(worker)
        thread.start()
    
    def start_plugin_search(self, plugin: SearchPlugin, query: str):
        """启动单个搜索插件搜索"""
        thread = QThread()
        worker = SearchWorker(plugin, query)
        
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self.on_plugin_results_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self.search_threads.append(thread)
        self.search_workers.append(worker)
        thread.start()
    
    def on_local_results_ready(self, results: List):
        """处理本地搜索结果"""
        for item, score in results:
            if hasattr(item.data, 'get_name'):  # 确保是插件对象
                self._add_plugin_to_list(item.data, is_search_result=False)
    
    def on_plugin_results_ready(self, plugin_name: str, results: List[SearchResult]):
        """处理搜索插件结果"""
        # 找到对应的插件对象
        plugin = None
        for p in self.search_plugins:
            if p.get_name() == plugin_name:
                plugin = p
                break
        
        if plugin:
            for result in results:
                self._add_plugin_to_list(plugin, is_search_result=True, search_result=result)
    
    def stop_all_searches(self):
        """停止所有正在进行的搜索"""
        for thread in self.search_threads[:]:
            try:
                if thread and thread.isRunning():
                    thread.quit()
                    thread.wait(1000)  # 等待最多1秒
            except RuntimeError:
                # 线程对象已被删除，忽略
                pass
        
        self.search_threads.clear()
        self.search_workers.clear()
    
    def perform_search(self, text: str):
        """保留原有接口以兼容性（已弃用，使用异步搜索）"""
        # 这个方法现在只是为了兼容性，实际搜索通过异步方式进行
        pass
    
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
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止所有搜索线程
        self.stop_all_searches()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
