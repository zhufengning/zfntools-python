# plugins/start_menu_search/tool.py

import os
import subprocess
import json
import time
import threading
import locale
from plugin_system import PluginType, SearchResult, SearchPlugin
from search_engine import SearchableItem

TOOL_NAME = "开始菜单搜索"
TOOL_DESCRIPTION = "搜索Windows开始菜单和应用商店中的应用程序"
PLUGIN_TYPE = PluginType.SEARCH

class StartMenuSearchPlugin(SearchPlugin):
    """开始菜单和应用商店搜索插件"""
    
    def __init__(self, plugin_dir: str = ""):
        super().__init__(plugin_dir)
        self.cached_apps = []
        self.last_update_time = 0
        self.update_interval = 15  # 15秒
        self.update_thread = None
        # Initial cache population in a separate thread to not block startup
        self.update_thread = threading.Thread(target=self._update_app_cache, daemon=True)
        self.update_thread.start()
    
    def get_name(self):
        return TOOL_NAME
    
    def get_description(self):
        return TOOL_DESCRIPTION
    
    def get_type(self):
        return PLUGIN_TYPE
    
    def _update_app_cache(self):
        """更新应用程序缓存"""
        self.cached_apps = self._get_all_apps()
        self.last_update_time = time.time()

    def _get_all_apps(self):
        """获取所有开始菜单和应用商店的应用程序"""
        apps = []
        try:
            ps_command = 'Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress'
            powershell_cmd = ['powershell', '-Command', ps_command]
            
            # 以二进制模式捕获输出，然后尝试不同的编码
            result = subprocess.run(powershell_cmd, capture_output=True, text=False)
            
            # 尝试解码输出
            stdout_text = ""
            stderr_text = ""
            
            if result.stdout:
                try:
                    # 首先尝试 UTF-8
                    stdout_text = result.stdout.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # 如果 UTF-8 失败，尝试系统默认编码
                        stdout_text = result.stdout.decode(locale.getpreferredencoding())
                    except UnicodeDecodeError:
                        try:
                            # 最后尝试 GBK（Windows 中文系统常用）
                            stdout_text = result.stdout.decode('gbk')
                        except UnicodeDecodeError:
                            # 如果都失败，使用 errors='ignore' 忽略错误字符
                            stdout_text = result.stdout.decode('utf-8', errors='ignore')
            
            if result.stderr:
                try:
                    stderr_text = result.stderr.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        stderr_text = result.stderr.decode(locale.getpreferredencoding())
                    except UnicodeDecodeError:
                        try:
                            stderr_text = result.stderr.decode('gbk')
                        except UnicodeDecodeError:
                            stderr_text = result.stderr.decode('utf-8', errors='ignore')
            
            # 创建一个模拟的 result 对象，包含解码后的文本
            class DecodedResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = DecodedResult(result.returncode, stdout_text, stderr_text)

            if result.stderr:
                print(f"PowerShell命令错误输出: {result.stderr}")
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    # The output might be a single JSON object or an array of them, each on a new line
                    # We need to handle this by splitting lines and parsing each
                    json_text = result.stdout.strip()
                    # If the output is a stream of json objects, it needs to be wrapped in brackets to be a valid json array
                    if not json_text.startswith('['):
                        json_text = f'[{",".join(json_text.splitlines())}]'

                    all_apps = json.loads(json_text)
                    
                    for app in all_apps:
                        name = app.get('Name')
                        app_id = app.get('AppID')
                        if name and app_id:
                            item = SearchableItem(
                                title=name,
                                description=f"应用: {name}",
                                data={'type': 'app', 'app_id': app_id},
                                keywords=[name.replace(' ', ''), name.replace('-', '')]
                            )
                            apps.append(item)
                            
                except json.JSONDecodeError as e:
                    print(f"JSON解析失败: {e}")
                    # print(f"无法解析的JSON内容: {result.stdout}") # This can be very long
                    
        except Exception as e:
            print(f"获取所有应用时发生错误: {e}")
        
        return apps
    
    def search(self, query):
        """搜索开始菜单和应用商店应用程序"""
        # 检查是否需要后台更新缓存
        if (time.time() - self.last_update_time > self.update_interval):
            if self.update_thread is None or not self.update_thread.is_alive():
                # 在后台线程中更新缓存
                self.update_thread = threading.Thread(target=self._update_app_cache, daemon=True)
                self.update_thread.start()

        # 使用缓存的列表进行搜索
        return self.search_items(query, self.cached_apps, max_results=15)
    
    def execute(self, result_data):
        """启动应用程序"""
        try:
            if result_data.get('type') == 'app':
                app_id = result_data['app_id']
                # Using Start-Process with Shell:AppsFolder to launch the app by its AppID
                command = f'Start-Process "shell:AppsFolder\\{app_id}"'
                subprocess.run(['powershell', '-Command', command], check=True)
        except Exception as e:
            print(f"启动应用程序失败: {e}")
    
    def execute_result(self, result):
        """执行搜索结果"""
        self.execute(result.data)