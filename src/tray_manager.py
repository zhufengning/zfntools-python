# tray_manager.py
import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, parent, icon_path: str = None):
        """
        初始化托盘管理器
        
        Args:
            parent: 父窗口对象
            icon_path: 托盘图标路径，如果为None则使用默认路径
        """
        self.parent = parent
        self.tray_icon = QSystemTrayIcon(parent)
        
        # 设置图标
        if icon_path is None:
            icon_path = os.path.join(os.path.dirname(__file__), 'plugins', 'emoji', 'appicon.png')
        
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            print(f"Warning: Tray icon not found at {icon_path}")
        
        # 设置提示文本
        self.tray_icon.setToolTip("Python 工具箱")
        
        # 创建菜单
        self._create_menu()
        
        # 连接信号
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
    
    def _create_menu(self):
        """创建托盘菜单"""
        tray_menu = QMenu()
        
        toggle_action = QAction("显示/隐藏", self.parent)
        toggle_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(toggle_action)
        
        exit_action = QAction("退出", self.parent)
        exit_action.triggered.connect(self.parent.exit_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
    
    def _on_tray_icon_activated(self, reason):
        """处理托盘图标点击事件"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger or \
           reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
    
    def toggle_window_visibility(self):
        """切换主窗口的可见性"""
        if self.parent.isVisible():
            self.parent.hide()
        else:
            self.parent.show_and_raise()
