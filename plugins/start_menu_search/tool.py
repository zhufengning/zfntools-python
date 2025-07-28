# plugins/start_menu_search/tool.py

import os
import subprocess
import winreg
from typing import List
from plugin_system import PluginType, SearchResult

TOOL_NAME = "开始菜单搜索"
TOOL_DESCRIPTION = "搜索Windows开始菜单中的应用程序"
PLUGIN_TYPE = PluginType.SEARCH

def search(query: str) -> List[SearchResult]:
    """搜索开始菜单中的应用程序"""
    results = []
    query_lower = query.lower()
    
    if len(query_lower) < 2:  # 至少输入2个字符才开始搜索
        return results
    
    # 搜索开始菜单快捷方式
    start_menu_paths = [
        os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
    ]
    
    for start_menu_path in start_menu_paths:
        if os.path.exists(start_menu_path):
            _search_directory(start_menu_path, query_lower, results)
    
    # 限制结果数量
    return results[:10]

def _search_directory(directory: str, query: str, results: List[SearchResult]):
    """递归搜索目录中的快捷方式"""
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.lnk'):
                    app_name = os.path.splitext(file)[0]
                    if query in app_name.lower():
                        file_path = os.path.join(root, file)
                        results.append(SearchResult(
                            title=app_name,
                            description=f"应用程序 - {file_path}",
                            plugin_name=TOOL_NAME,
                            data={'path': file_path, 'type': 'shortcut'}
                        ))
    except Exception as e:
        print(f"搜索目录 {directory} 时出错: {e}")

def execute_result(result: SearchResult) -> None:
    """执行搜索结果"""
    try:
        if result.data and result.data.get('type') == 'shortcut':
            path = result.data.get('path')
            if path and os.path.exists(path):
                # 使用Windows shell执行快捷方式
                os.startfile(path)
            else:
                print(f"快捷方式文件不存在: {path}")
    except Exception as e:
        print(f"启动应用程序失败: {e}")