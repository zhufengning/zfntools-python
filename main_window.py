# main_window.py
import sys
import os
import socket
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QLabel, QHBoxLayout,
    QFrame, QTabBar, QMessageBox, QSystemTrayIcon, QMenu
)
from PySide6.QtGui import QIcon, Qt, QKeyEvent, QAction
from PySide6.QtCore import QSize, QUrl, QThread, Signal, QObject, QTimer
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtWebEngineWidgets import QWebEngineView
from plugin_system import PluginLoader, PluginType, BasePlugin, WidgetPlugin, ActionPlugin, SearchPlugin, WebPlugin, SearchResult
from search_engine import SearchableItem, get_search_engine
from typing import List

# 导入新的模块
from settings_manager import SettingsManager
from search_workers import SearchWorker, LocalSearchWorker

PORT_FILE = ".port"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 工具箱")
        self.setGeometry(100, 100, 900, 600)

        # 初始化设置管理器
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.settings_manager = SettingsManager(data_dir)

        # 加载所有插件
        self.plugins = self.load_plugins()
        self.search_plugins = [p for p in self.plugins if isinstance(p, SearchPlugin)]

        # 初始化搜索引擎
        self.setup_search_engine()
        
        # 异步搜索相关
        self.search_threads = []
        self.search_workers = []
        self.current_search_query = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.start_async_search)
        self.pending_results = {}

        # --- Main Tab Widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # --- Home Tab (Tool List) ---
        self.home_tab = QWidget()
        self.setup_home_tab()
        self.tab_widget.addTab(self.home_tab, "首页")
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        self.update_tool_list()

        # 启动时聚焦到搜索框
        self.search_bar.setFocus()

        # 创建系统托盘图标
        self.create_tray_icon()

        # 初始化UDP监听
        self.init_udp_listener()

    def init_udp_listener(self):
        """初始化UDP监听器用于唤醒窗口"""
        self.udp_socket = QUdpSocket(self)
        # 绑定到任意可用端口
        if self.udp_socket.bind(QHostAddress.LocalHost, 0):
            port = self.udp_socket.localPort()
            try:
                with open(PORT_FILE, "w") as f:
                    f.write(str(port))
            except IOError as e:
                print(f"Error writing port file: {e}")
            self.udp_socket.readyRead.connect(self.handle_udp_message)
        else:
            print("Error: Unable to bind to UDP socket.")

    def handle_udp_message(self):
        """处理收到的UDP消息"""
        while self.udp_socket.hasPendingDatagrams():
            datagram = self.udp_socket.receiveDatagram()
            # 不需要关心内容，收到就唤醒
            self.show_and_raise()

    def show_and_raise(self):
        """显示窗口并置于顶层"""
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()
            if self.tab_widget.currentWidget() == self.home_tab:
                self.search_bar.setFocus()

    def create_tray_icon(self):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(__file__), 'plugins', 'emoji', 'appicon.png')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            print(f"Warning: Tray icon not found at {icon_path}")

        self.tray_icon.setToolTip("Python 工具箱")
        tray_menu = QMenu()
        toggle_action = QAction("显示/隐藏", self)
        toggle_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(toggle_action)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_application)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def toggle_window_visibility(self):
        """切换主窗口的可见性"""
        if self.isVisible():
            self.hide()
        else:
            self.show_and_raise()

    def on_tray_icon_activated(self, reason):
        """处理托盘图标点击事件"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
            
    def cleanup_port_file(self):
        """清理端口文件"""
        if os.path.exists(PORT_FILE):
            try:
                os.remove(PORT_FILE)
            except OSError as e:
                print(f"Error removing port file: {e}")

    def exit_application(self):
        """退出应用程序"""
        self.cleanup_port_file()
        self.stop_all_searches()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def load_plugins(self):
        """加载所有插件"""
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        return PluginLoader.load_plugins(plugins_dir)
    
    def setup_search_engine(self):
        """设置搜索引擎并添加本地插件"""
        search_engine = get_search_engine()
        search_engine.clear()
        
        for plugin in self.plugins:
            if not isinstance(plugin, SearchPlugin):
                item = SearchableItem(
                    title=plugin.get_name(),
                    description=plugin.get_description(),
                    data=plugin
                )
                search_engine.add_item(item)

    def setup_home_tab(self):
        """Sets up the layout and widgets for the home tab."""
        layout = QVBoxLayout(self.home_tab)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索工具和应用程序...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        self.search_bar.keyPressEvent = self.search_bar_key_press_event
        layout.addWidget(self.search_bar)

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
            if self.tool_list_widget.count() > 0:
                current_row = self.tool_list_widget.currentRow()
                if current_row < 0:
                    self.tool_list_widget.setCurrentRow(0)
                elif current_row < self.tool_list_widget.count() - 1:
                    self.tool_list_widget.setCurrentRow(current_row + 1)
        elif event.key() == Qt.Key_Up:
            if self.tool_list_widget.count() > 0:
                current_row = self.tool_list_widget.currentRow()
                if current_row < 0:
                    self.tool_list_widget.setCurrentRow(self.tool_list_widget.count() - 1)
                elif current_row > 0:
                    self.tool_list_widget.setCurrentRow(current_row - 1)
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.tool_list_widget.count() > 0:
                current_item = self.tool_list_widget.currentItem()
                if current_item:
                    self.handle_item_activation(current_item)
                else:
                    self.tool_list_widget.setCurrentRow(0)
                    self.handle_item_activation(self.tool_list_widget.currentItem())
        else:
            QLineEdit.keyPressEvent(self.search_bar, event)
    
    def list_key_press_event(self, event: QKeyEvent):
        """列表键盘事件处理"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            current_item = self.tool_list_widget.currentItem()
            if current_item:
                self.handle_item_activation(current_item)
        elif event.key() == Qt.Key_Escape:
            self.hide()
        else:
            QListWidget.keyPressEvent(self.tool_list_widget, event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """处理主窗口的按键事件"""
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def _add_plugin_to_list(self, plugin: BasePlugin, is_search_result: bool = False, search_result: SearchResult = None):
        """将插件添加到列表中"""
        item = QListWidgetItem()
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
            
            item.setData(Qt.UserRole, {'type': 'search_result', 'result': search_result, 'plugin': plugin})
        else:
            name_label = QLabel(f"<b>{plugin.get_name()}</b>")
            desc_label = QLabel(f"<small>{plugin.get_description()}</small>")
            type_label = QLabel(f"<i>类型: {self._get_plugin_type_display(plugin.get_type())}</i>")
            type_label.setStyleSheet("color: #666;")
            
            layout.addWidget(name_label)
            layout.addWidget(desc_label)
            layout.addWidget(type_label)
            
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
        self.search_timer.start(300)

    def start_async_search(self):
        """开始异步搜索"""
        self.stop_all_searches()
        
        query = self.current_search_query
        if not query:
            self.update_tool_list()
            return
        
        self.tool_list_widget.clear()
        self.pending_results = {}
        
        self.start_local_search(query)
        
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
            if hasattr(item.data, 'get_name'):
                self._add_plugin_to_list(item.data, is_search_result=False)
    
    def on_plugin_results_ready(self, plugin_name: str, results: List[SearchResult]):
        """处理搜索插件结果"""
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
                    thread.wait(1000)
            except RuntimeError:
                pass
        
        self.search_threads.clear()
        self.search_workers.clear()
    
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
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "执行失败", f"执行搜索结果时出错: {e}")

    def close_tab(self, index):
        """Closes a tab."""
        if self.tab_widget.widget(index) == self.home_tab:
            return
            
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)
    
    def closeEvent(self, event):
        """重写关闭事件，实现隐藏到托盘"""
        event.ignore()
        self.hide()