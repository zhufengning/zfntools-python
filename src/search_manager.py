# search_manager.py
from PySide6.QtCore import QTimer, QThread, Qt as QtCore, QObject, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import Qt
from plugin_system import BasePlugin, SearchPlugin, SearchResult, PluginType
from search_engine import SearchableItem, get_search_engine
from search_workers import SearchWorker, LocalSearchWorker
from typing import List, Callable


class SearchManager(QObject):
    """搜索管理器，负责本地和插件搜索"""
    
    # 定义信号用于线程安全的UI更新
    add_local_result = Signal(object)  # BasePlugin
    add_search_result = Signal(object, object)  # SearchPlugin, SearchResult
    
    def __init__(self, plugins: List[BasePlugin], tool_list_widget: QListWidget):
        """
        初始化搜索管理器
        
        Args:
            plugins: 所有插件列表
            tool_list_widget: 显示结果的列表控件
        """
        super().__init__()
        self.plugins = plugins
        self.search_plugins = [p for p in plugins if isinstance(p, SearchPlugin)]
        self.tool_list_widget = tool_list_widget
        
        # 连接信号到槽函数
        self.add_local_result.connect(self._add_local_result_slot)
        self.add_search_result.connect(self._add_search_result_slot)
        
        # 搜索状态
        self.search_threads = []
        self.search_workers = []
        self.current_search_query = ""
        self.pending_results = {}
        
        # 防抖定时器
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        
        # 初始化搜索引擎
        self._setup_search_engine()
    
    def _setup_search_engine(self):
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
    
    def set_search_callback(self, callback: Callable):
        """设置搜索回调函数"""
        self.search_timer.timeout.connect(callback)
    
    def on_search_text_changed(self, text: str):
        """搜索文本变化时的处理（防抖）"""
        self.current_search_query = text.strip()
        self.search_timer.stop()
        self.search_timer.start(300)
    
    def start_search(self, query: str = None):
        """开始异步搜索"""
        if query is None:
            query = self.current_search_query
        
        self.stop_all_searches()
        
        if not query:
            return False
        
        self.tool_list_widget.clear()
        self.pending_results = {}
        
        self._start_local_search(query)
        
        for search_plugin in self.search_plugins:
            self._start_plugin_search(search_plugin, query)
        
        return True
    
    def _start_local_search(self, query: str):
        """启动本地插件搜索"""
        print(f"[SearchManager] 启动本地搜索: {query}")
        thread = QThread()
        worker = LocalSearchWorker(query)
        
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self._on_local_results_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self.search_threads.append(thread)
        self.search_workers.append(worker)
        thread.start()
        print(f"[SearchManager] 本地搜索线程已启动")
    
    def _start_plugin_search(self, plugin: SearchPlugin, query: str):
        """启动单个搜索插件搜索"""
        print(f"[SearchManager] 启动插件搜索: {plugin.get_name()}")
        thread = QThread()
        worker = SearchWorker(plugin, query)
        
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self._on_plugin_results_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self.search_threads.append(thread)
        self.search_workers.append(worker)
        thread.start()
        print(f"[SearchManager] 插件搜索线程已启动: {plugin.get_name()}")
    
    def _on_local_results_ready(self, results: List):
        """处理本地搜索结果"""
        print(f"[SearchManager] 收到本地搜索结果: {len(results)} 条")
        # 使用信号发射，Qt会自动在主线程中调用槽函数
        for item, score in results:
            if hasattr(item.data, 'get_name'):
                print(f"[SearchManager] 发射信号添加本地结果: {item.data.get_name()}")
                self.add_local_result.emit(item.data)
    
    def _on_plugin_results_ready(self, plugin_name: str, results: List[SearchResult]):
        """处理搜索插件结果"""
        print(f"[SearchManager] 收到插件搜索结果: {plugin_name}, {len(results)} 条")
        plugin = None
        for p in self.search_plugins:
            if p.get_name() == plugin_name:
                plugin = p
                break
        
        if plugin:
            # 使用信号发射，Qt会自动在主线程中调用槽函数
            for result in results:
                print(f"[SearchManager] 发射信号添加插件结果: {result.title}")
                self.add_search_result.emit(plugin, result)
    
    def _add_local_result_slot(self, plugin: BasePlugin):
        """槽函数：添加本地搜索结果（在主线程中执行）"""
        print(f"[SearchManager] 槽函数接收本地结果: {plugin.get_name()}")
        self.add_plugin_to_list(plugin, is_search_result=False)
    
    def _add_search_result_slot(self, plugin: SearchPlugin, result: SearchResult):
        """槽函数：添加搜索插件结果（在主线程中执行）"""
        print(f"[SearchManager] 槽函数接收插件结果: {result.title}")
        self.add_plugin_to_list(plugin, is_search_result=True, search_result=result)
    
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
    
    def add_plugin_to_list(self, plugin: BasePlugin, is_search_result: bool = False, 
                          search_result: SearchResult = None):
        """将插件添加到列表中"""
        try:
            print(f"[SearchManager] 开始添加到列表: {plugin.get_name() if plugin else 'None'}")
            item = QListWidgetItem()
            print(f"[SearchManager] 创建QListWidgetItem成功")
            widget = QWidget()
            print(f"[SearchManager] 创建QWidget成功")
            layout = QVBoxLayout(widget)
            print(f"[SearchManager] 创建QVBoxLayout成功")
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
            print(f"[SearchManager] 开始添加到tool_list_widget")
            self.tool_list_widget.addItem(item)
            print(f"[SearchManager] addItem成功")
            self.tool_list_widget.setItemWidget(item, widget)
            print(f"[SearchManager] setItemWidget成功")
            
            # 如果这是第一项，自动选中
            if self.tool_list_widget.count() == 1:
                self.tool_list_widget.setCurrentRow(0)
                print(f"[SearchManager] 自动选中第一项")
        except Exception as e:
            print(f"[SearchManager] 错误: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def _get_plugin_type_display(plugin_type: PluginType) -> str:
        """获取插件类型的显示名称"""
        type_map = {
            PluginType.WIDGET: "界面工具",
            PluginType.ACTION: "快捷操作",
            PluginType.SEARCH: "搜索工具",
            PluginType.WEB: "Web应用"
        }
        return type_map.get(plugin_type, "未知类型")
    
    def update_tool_list(self):
        """显示所有已加载的插件"""
        self.tool_list_widget.clear()
        for plugin in self.plugins:
            self.add_plugin_to_list(plugin, is_search_result=False)
