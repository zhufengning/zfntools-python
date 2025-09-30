# search_workers.py
from PySide6.QtCore import QObject, Signal
from plugin_system import SearchPlugin
from search_engine import get_search_engine
from typing import List

class SearchWorker(QObject):
    """异步搜索工作器，用于在后台执行插件搜索"""
    results_ready = Signal(str, list)  # plugin_name, results
    finished = Signal(str)  # plugin_name
    
    def __init__(self, plugin: SearchPlugin, query: str):
        super().__init__()
        self.plugin = plugin
        self.query = query
    
    def run(self):
        """执行搜索"""
        try:
            results = self.plugin.search(self.query)
            self.results_ready.emit(self.plugin.get_name(), results)
        except Exception as e:
            print(f"Search error in {self.plugin.get_name()}: {e}")
        finally:
            self.finished.emit(self.plugin.get_name())

class LocalSearchWorker(QObject):
    """本地搜索工作器，用于搜索本地插件"""
    results_ready = Signal(list)  # local results
    finished = Signal()
    
    def __init__(self, query: str):
        super().__init__()
        self.query = query
    
    def run(self):
        """执行本地搜索"""
        try:
            search_engine = get_search_engine()
            results = search_engine.search(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            print(f"Local search error: {e}") 
        finally:
            self.finished.emit()