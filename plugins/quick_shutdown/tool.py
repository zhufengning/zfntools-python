# plugins/quick_shutdown/tool.py

import os
import subprocess
from plugin_system import PluginType

TOOL_NAME = "快捷关机"
TOOL_DESCRIPTION = "立即关闭计算机"
PLUGIN_TYPE = PluginType.ACTION

def execute():
    """执行关机命令"""
    try:
        # 在 Windows 上隐藏控制台窗口（特别是在 PyInstaller 打包后）
        startupinfo = None
        if os.name == 'nt':  # Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # Windows关机命令
        subprocess.run(["shutdown", "/s", "/t", "0"], check=True, startupinfo=startupinfo)
    except subprocess.CalledProcessError as e:
        print(f"关机失败: {e}")
    except Exception as e:
        print(f"执行关机命令时出错: {e}")