# main_window.py
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QTabWidget, QTabBar, QApplication
)
from PySide6.QtGui import Qt, QKeyEvent
from PySide6.QtCore import QTimer

# 导入新的模块
from settings_manager import SettingsManager
from tray_manager import TrayManager
from udp_listener import UdpListener
from search_manager import SearchManager
from plugin_manager import PluginManager


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("zfnbox")
        self.setGeometry(100, 100, 900, 600)

        # 初始化设置管理器
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.settings_manager = SettingsManager(data_dir)

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

        # 初始化插件管理器
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        self.plugin_manager = PluginManager(plugins_dir, self.tab_widget, self)
        
        # 初始化搜索管理器
        self.search_manager = SearchManager(
            self.plugin_manager.get_plugins(), 
            self.tool_list_widget,
            data_dir
        )
        self.search_manager.set_search_callback(self.start_async_search)
        
        # 显示所有插件
        self.search_manager.update_tool_list()

        # 启动时聚焦到搜索框
        self.search_bar.setFocus()

        # 创建系统托盘图标
        self.tray_manager = TrayManager(self)

        # 初始化UDP监听
        self.udp_listener = UdpListener(self)

    def setup_home_tab(self):
        """设置首页标签"""
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

    def on_search_text_changed(self, text: str):
        """搜索文本变化时的处理"""
        self.search_manager.on_search_text_changed(text)

    def start_async_search(self):
        """开始异步搜索"""
        if not self.search_manager.start_search():
            self.search_manager.update_tool_list()

    def show_and_raise(self):
        """显示窗口并置于顶层"""
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            if self.isMinimized():
                self.showNormal()
            self.show()
            
            # 置顶会导致窗口闪烁，所以不使用
            # # 设置窗口标志以置顶
            # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            # self.show()
            
            # # 移除置顶标志（只是临时置顶）
            # self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            # self.show()
            
            self.raise_()
            wh = self.windowHandle()
            if wh is not None:
                wh.requestActivate()
            QApplication.setActiveWindow(self)
            self.activateWindow()
            QTimer.singleShot(0, self._ensure_activated)
            
            if self.tab_widget.currentWidget() == self.home_tab:
                self.search_bar.setFocus(Qt.ActiveWindowFocusReason)

    def _ensure_activated(self):
        self.raise_()
        wh = self.windowHandle()
        if wh is not None:
            wh.requestActivate()
        QApplication.setActiveWindow(self)
        self.activateWindow()
        if self.tab_widget.currentWidget() == self.home_tab:
            self.search_bar.setFocus(Qt.ActiveWindowFocusReason)

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
            self._handle_escape()
        else:
            QListWidget.keyPressEvent(self.tool_list_widget, event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """处理主窗口的按键事件"""
        if event.key() == Qt.Key_Escape:
            self._handle_escape()
        else:
            super().keyPressEvent(event)
    
    def _handle_escape(self):
        """处理ESC键：如果搜索框有内容则清空，否则隐藏窗口"""
        if self.search_bar.text():
            self.search_bar.clear()
            self.search_manager.update_tool_list()
        else:
            self.hide()

    def handle_item_activation(self, item):
        """处理项目激活（双击）"""
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'plugin':
            self.search_manager.record_usage(data)
            self.plugin_manager.open_plugin(data['plugin'])
        elif data['type'] == 'search_result':
            self.search_manager.record_usage(data)
            self.plugin_manager.execute_search_result(data['result'], data['plugin'])
        
        # 清空搜索框并显示所有插件
        self.search_bar.clear()
        self.search_manager.update_tool_list()

    def close_tab(self, index):
        """关闭标签页"""
        if self.tab_widget.widget(index) == self.home_tab:
            return
            
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)
    
    def exit_application(self):
        """退出应用程序"""
        UdpListener.cleanup_port_file()
        self.search_manager.stop_all_searches()
        QApplication.quit()
    
    def closeEvent(self, event):
        """重写关闭事件，实现隐藏到托盘"""
        event.ignore()
        self.hide()
