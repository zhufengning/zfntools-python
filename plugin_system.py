# plugin_system.py

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget
import json
import os

class PluginType(Enum):
    """插件类型枚举"""
    WIDGET = "widget"          # 传统的界面插件
    ACTION = "action"          # 无界面插件，点击执行
    SEARCH = "search"          # 搜索插件
    WEB = "web"                # Web插件

class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.name = "未命名插件"
        self.description = ""
        self.plugin_type = PluginType.WIDGET
    
    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取插件描述"""
        pass
    
    @abstractmethod
    def get_type(self) -> PluginType:
        """获取插件类型"""
        pass

class WidgetPlugin(BasePlugin):
    """界面插件"""
    
    @abstractmethod
    def create_widget(self) -> QWidget:
        """创建插件界面"""
        pass

class ActionPlugin(BasePlugin):
    """无界面插件"""
    
    @abstractmethod
    def execute(self) -> None:
        """执行插件功能"""
        pass

class SearchResult:
    """搜索结果"""
    
    def __init__(self, title: str, description: str, plugin_name: str, data: Any = None):
        self.title = title
        self.description = description
        self.plugin_name = plugin_name
        self.data = data

class SearchPlugin(BasePlugin):
    """搜索插件"""
    
    @abstractmethod
    def search(self, query: str) -> List[SearchResult]:
        """搜索功能"""
        pass
    
    @abstractmethod
    def execute_result(self, result: SearchResult) -> None:
        """执行搜索结果"""
        pass

class WebPlugin(BasePlugin):
    """Web插件"""
    
    def __init__(self, plugin_dir: str, manifest: Dict[str, Any]):
        super().__init__(plugin_dir)
        self.manifest = manifest
        self.name = manifest.get('name', '未命名Web插件')
        self.description = manifest.get('description', '')
        self.entry_file = manifest.get('entry', 'index.html')
        self.plugin_type = PluginType.WEB
    
    def get_name(self) -> str:
        return self.name
    
    def get_description(self) -> str:
        return self.description
    
    def get_type(self) -> PluginType:
        return self.plugin_type
    
    def get_entry_path(self) -> str:
        """获取入口文件的完整路径"""
        return os.path.join(self.plugin_dir, self.entry_file)

class PluginLoader:
    """插件加载器"""
    
    @staticmethod
    def load_plugins(plugins_dir: str) -> List[BasePlugin]:
        """加载所有插件"""
        plugins = []
        
        if not os.path.isdir(plugins_dir):
            return plugins
        
        for plugin_name in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, plugin_name)
            if not os.path.isdir(plugin_dir):
                continue
            
            try:
                plugin = PluginLoader._load_single_plugin(plugin_dir, plugin_name)
                if plugin:
                    plugins.append(plugin)
            except Exception as e:
                print(f"无法加载插件 '{plugin_name}': {e}")
        
        return plugins
    
    @staticmethod
    def _load_single_plugin(plugin_dir: str, plugin_name: str) -> Optional[BasePlugin]:
        """加载单个插件"""
        # 检查是否为Web插件
        manifest_path = os.path.join(plugin_dir, 'manifest.json')
        if os.path.isfile(manifest_path):
            return PluginLoader._load_web_plugin(plugin_dir, manifest_path)
        
        # 检查是否为Python插件
        tool_file = os.path.join(plugin_dir, 'tool.py')
        if os.path.isfile(tool_file):
            return PluginLoader._load_python_plugin(plugin_dir, plugin_name, tool_file)
        
        return None
    
    @staticmethod
    def _load_web_plugin(plugin_dir: str, manifest_path: str) -> Optional[WebPlugin]:
        """加载Web插件"""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            return WebPlugin(plugin_dir, manifest)
        except Exception as e:
            print(f"无法加载Web插件manifest: {e}")
            return None
    
    @staticmethod
    def _load_python_plugin(plugin_dir: str, plugin_name: str, tool_file: str) -> Optional[BasePlugin]:
        """加载Python插件"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", tool_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 检查插件类型
        plugin_type = getattr(module, 'PLUGIN_TYPE', PluginType.WIDGET)
        
        if plugin_type == PluginType.WIDGET:
            return PluginLoader._create_widget_plugin(plugin_dir, module)
        elif plugin_type == PluginType.ACTION:
            return PluginLoader._create_action_plugin(plugin_dir, module)
        elif plugin_type == PluginType.SEARCH:
            return PluginLoader._create_search_plugin(plugin_dir, module)
        
        return None
    
    @staticmethod
    def _create_widget_plugin(plugin_dir: str, module) -> Optional[WidgetPlugin]:
        """创建界面插件包装器"""
        class WidgetPluginWrapper(WidgetPlugin):
            def __init__(self):
                super().__init__(plugin_dir)
                self.name = getattr(module, 'TOOL_NAME', '未命名工具')
                self.description = getattr(module, 'TOOL_DESCRIPTION', '')
                self.widget_class = getattr(module, 'ToolWidget')
            
            def get_name(self) -> str:
                return self.name
            
            def get_description(self) -> str:
                return self.description
            
            def get_type(self) -> PluginType:
                return PluginType.WIDGET
            
            def create_widget(self) -> QWidget:
                return self.widget_class()
        
        return WidgetPluginWrapper()
    
    @staticmethod
    def _create_action_plugin(plugin_dir: str, module) -> Optional[ActionPlugin]:
        """创建无界面插件包装器"""
        class ActionPluginWrapper(ActionPlugin):
            def __init__(self):
                super().__init__(plugin_dir)
                self.name = getattr(module, 'TOOL_NAME', '未命名工具')
                self.description = getattr(module, 'TOOL_DESCRIPTION', '')
                self.execute_func = getattr(module, 'execute')
            
            def get_name(self) -> str:
                return self.name
            
            def get_description(self) -> str:
                return self.description
            
            def get_type(self) -> PluginType:
                return PluginType.ACTION
            
            def execute(self) -> None:
                self.execute_func()
        
        return ActionPluginWrapper()
    
    @staticmethod
    def _create_search_plugin(plugin_dir: str, module) -> Optional[SearchPlugin]:
        """创建搜索插件包装器"""
        class SearchPluginWrapper(SearchPlugin):
            def __init__(self):
                super().__init__(plugin_dir)
                self.name = getattr(module, 'TOOL_NAME', '未命名工具')
                self.description = getattr(module, 'TOOL_DESCRIPTION', '')
                self.search_func = getattr(module, 'search')
                self.execute_result_func = getattr(module, 'execute_result')
            
            def get_name(self) -> str:
                return self.name
            
            def get_description(self) -> str:
                return self.description
            
            def get_type(self) -> PluginType:
                return PluginType.SEARCH
            
            def search(self, query: str) -> List[SearchResult]:
                return self.search_func(query)
            
            def execute_result(self, result: SearchResult) -> None:
                self.execute_result_func(result)
        
        return SearchPluginWrapper()