# Python 工具箱

一个基于 PySide6 的多标签页工具箱应用程序，支持可扩展的插件系统。

## 项目简介

Python 工具箱是一个桌面应用程序，提供了一个统一的界面来使用各种实用工具。应用程序采用插件架构，可以轻松添加新的工具功能。

## 主要功能

- **多标签页界面**：支持同时打开多个工具，每个工具在独立的标签页中运行
- **多类型插件系统**：支持界面插件、无界面插件、搜索插件和Web插件
- **智能搜索**：在首页提供统一搜索功能，同时搜索本地插件和外部资源
- **可扩展架构**：开发者可以轻松添加各种类型的插件

## 内置插件

### 界面插件 (Widget Plugins)

#### 1. 进制转换器
- **功能**：在二进制、十进制、十六进制之间转换数字
- **特点**：实时转换，输入任意进制的数字，自动显示其他进制的对应值

#### 2. 颜色选择器
- **功能**：从调色板中选择颜色并获取其不同格式的值
- **支持格式**：HEX、RGB、HSL
- **特点**：可视化颜色预览，自动调整文本颜色以确保对比度

### 无界面插件 (Action Plugins)

#### 3. 快捷关机
- **功能**：一键关闭计算机
- **特点**：点击后确认执行，无需打开额外界面

### 搜索插件 (Search Plugins)

#### 4. 开始菜单搜索
- **功能**：搜索Windows开始菜单中的应用程序
- **特点**：在主搜索框中输入应用名称，直接启动应用程序

### Web插件 (Web Plugins)

#### 5. CyberChef
- **功能**：集成了 CyberChef 工具的本地版本
- **用途**：数据分析、编码解码、加密解密等
- **特点**：在独立标签页中运行，支持完整的Web功能

## 技术栈

- **Python 3.13+**：主要编程语言
- **PySide6**：GUI框架，提供现代化的用户界面
- **PySide6-WebEngine**：Web插件支持
- **Qt Designer**：用于设计用户界面（可选）
- **模块化架构**：支持多种类型的插件系统

## 插件开发指南

### 界面插件 (Widget Plugin)

在 `plugins/your_plugin_name/tool.py` 中定义：

```python
from PySide6.QtWidgets import QWidget
from plugin_system import PluginType

TOOL_NAME = "插件名称"
TOOL_DESCRIPTION = "插件描述"
PLUGIN_TYPE = PluginType.WIDGET

class ToolWidget(QWidget):
    def __init__(self):
        super().__init__()
        # 初始化界面
```

### 无界面插件 (Action Plugin)

```python
from plugin_system import PluginType

TOOL_NAME = "插件名称"
TOOL_DESCRIPTION = "插件描述"
PLUGIN_TYPE = PluginType.ACTION

def execute():
    # 执行操作的代码
    pass
```

### 搜索插件 (Search Plugin)

```python
from plugin_system import PluginType, SearchResult

TOOL_NAME = "插件名称"
TOOL_DESCRIPTION = "插件描述"
PLUGIN_TYPE = PluginType.SEARCH

def search(query):
    # 返回 SearchResult 列表
    return [SearchResult("标题", "描述", "数据")]

def execute(result_data):
    # 执行搜索结果
    pass
```

### Web插件 (Web Plugin)

在 `plugins/your_plugin_name/manifest.json` 中定义：

```json
{
    "name": "插件名称",
    "description": "插件描述",
    "version": "1.0.0",
    "entry": "index.html",
    "author": "作者",
    "homepage": "主页URL",
    "type": "web",
    "permissions": [],
    "tags": ["标签"]
}
```

## 项目结构

```
python-toolbox/
├── main.py                    # 主程序入口
├── plugin_system.py           # 插件系统核心
├── pyproject.toml            # 项目配置文件
├── requirements.txt          # 依赖列表
├── README.md                # 项目说明文档
└── plugins/                 # 插件目录
    ├── base_converter/      # 界面插件：进制转换器
    │   └── tool.py
    ├── color_picker/        # 界面插件：颜色选择器
    │   └── tool.py
    ├── quick_shutdown/      # 无界面插件：快捷关机
    │   └── tool.py
    ├── start_menu_search/   # 搜索插件：开始菜单搜索
    │   └── tool.py
    └── CyberChef/          # Web插件：CyberChef工具
        ├── manifest.json
        ├── index.html
        └── ...
```

## 安装和运行

### 环境要求

- Python 3.13 或更高版本
- uv 包管理器（推荐）

### 安装 uv

如果还没有安装 uv，请先安装：

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装依赖

使用 uv 安装项目依赖（推荐）：

```bash
uv sync
```

或者使用传统的 pip 方式：

```bash
pip install PySide6
```

### 运行应用

使用 uv 运行（推荐）：

```bash
uv run python main.py
```

或者激活虚拟环境后运行：

```bash
# 激活虚拟环境
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # macOS/Linux

# 运行应用
python main.py
```

## 开发插件

### 插件结构

每个插件都是 `plugins` 目录下的一个子目录，包含一个 `tool.py` 文件。插件文件需要定义以下内容：

```python
# plugins/your_tool/tool.py

from PySide6.QtWidgets import QWidget

# 工具名称（必需）
TOOL_NAME = "你的工具名称"

# 工具描述（必需）
TOOL_DESCRIPTION = "工具功能描述"

# 工具界面类（必需）
class ToolWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 在这里实现你的工具界面
        pass
```

### 插件开发指南

1. 在 `plugins` 目录下创建新的子目录
2. 在子目录中创建 `tool.py` 文件
3. 定义 `TOOL_NAME`、`TOOL_DESCRIPTION` 和 `ToolWidget` 类
4. `ToolWidget` 类继承自 `QWidget`，实现具体的工具功能
5. 重启应用程序，新插件将自动加载

## 特性

- **动态插件加载**：无需修改主程序代码即可添加新工具
- **标签页管理**：支持打开多个工具实例，可以关闭除首页外的任意标签页
- **搜索过滤**：在工具列表中快速搜索和过滤工具
- **错误处理**：插件加载失败时不会影响其他插件的正常运行

## 许可证

本项目采用开源许可证，具体许可证信息请查看项目根目录下的 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。在贡献代码之前，请确保：

1. 代码符合项目的编码规范
2. 新功能包含适当的测试
3. 更新相关文档

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。