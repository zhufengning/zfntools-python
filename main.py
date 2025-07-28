# main.py
import sys
import os
import importlib.util
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QLabel, QHBoxLayout,
    QFrame, QTabBar
)
from PySide6.QtGui import QIcon, Qt
from PySide6.QtCore import QSize

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 工具箱")
        self.setGeometry(100, 100, 900, 600)

        self.tools = self.load_tools()

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

    def load_tools(self):
        """Dynamically load tools from the 'plugins' directory."""
        tools = []
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        if not os.path.isdir(plugins_dir):
            return tools

        for tool_name in os.listdir(plugins_dir):
            tool_dir = os.path.join(plugins_dir, tool_name)
            tool_file = os.path.join(tool_dir, 'tool.py')
            if os.path.isfile(tool_file):
                try:
                    spec = importlib.util.spec_from_file_location(f"plugins.{tool_name}", tool_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    tools.append({
                        "name": getattr(module, 'TOOL_NAME', '未命名工具'),
                        "description": getattr(module, 'TOOL_DESCRIPTION', ''),
                        "widget_class": getattr(module, 'ToolWidget'),
                        "module": module
                    })
                except Exception as e:
                    print(f"无法加载工具 '{tool_name}': {e}")
        return tools

    def setup_home_tab(self):
        """Sets up the layout and widgets for the home tab."""
        layout = QVBoxLayout(self.home_tab)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索工具...")
        self.search_bar.textChanged.connect(self.filter_tools)
        layout.addWidget(self.search_bar)

        # Tool list
        self.tool_list_widget = QListWidget()
        self.tool_list_widget.itemDoubleClicked.connect(self.open_tool_from_list)
        self.tool_list_widget.setWordWrap(True)
        layout.addWidget(self.tool_list_widget)

    def update_tool_list(self):
        """Populates the tool list widget with all loaded tools."""
        self.tool_list_widget.clear()
        for tool in self.tools:
            item = QListWidgetItem()
            
            # Create a custom widget for the list item
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            name_label = QLabel(f"<b>{tool['name']}</b>")
            desc_label = QLabel(f"<small>{tool['description']}</small>")
            desc_label.setWordWrap(True)
            
            layout.addWidget(name_label)
            layout.addWidget(desc_label)
            
            item.setSizeHint(widget.sizeHint())
            self.tool_list_widget.addItem(item)
            self.tool_list_widget.setItemWidget(item, widget)
            
            # Store tool data in the item
            item.setData(Qt.UserRole, tool)


    def filter_tools(self, text):
        """Filters the tool list based on the search bar text."""
        text = text.lower()
        for i in range(self.tool_list_widget.count()):
            item = self.tool_list_widget.item(i)
            tool = item.data(Qt.UserRole)
            is_visible = text in tool['name'].lower() or text in tool['description'].lower()
            item.setHidden(not is_visible)

    def open_tool_from_list(self, item):
        """Opens the selected tool in a new tab."""
        tool_data = item.data(Qt.UserRole)
        self.open_tool(tool_data)

    def open_tool(self, tool_data):
        """Creates a new instance of a tool and opens it in a new tab."""
        try:
            tool_widget = tool_data["widget_class"]()
            tab_name = tool_data["name"]
            
            # Check if this tool is already open, if so, add a number
            open_tabs = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
            count = 1
            new_tab_name = tab_name
            while new_tab_name in open_tabs:
                count += 1
                new_tab_name = f"{tab_name} ({count})"

            index = self.tab_widget.addTab(tool_widget, new_tab_name)
            self.tab_widget.setCurrentIndex(index)
        except Exception as e:
            print(f"无法打开工具 '{tool_data['name']}': {e}")

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
