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
        # Windows关机命令
        subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"关机失败: {e}")
    except Exception as e:
        print(f"执行关机命令时出错: {e}")