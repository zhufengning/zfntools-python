# Python 工具箱

一个基于 PySide6 的多标签页工具箱应用程序，拥有一个支持多种插件类型的现代化、可扩展的插件系统。

## 项目简介

Python 工具箱是一个桌面应用程序，它提供了一个统一的、美观的界面来发现和使用各种实用工具。应用程序的核心是其插件架构，允许开发者轻松地创建和集成新的功能。

## 主要功能

- **多标签页界面**：支持同时打开多个工具，每个工具在独立的标签页中运行，互不干扰。
- **现代化插件系统**：
  - **多类型支持**：支持界面插件、无界面插件、搜索插件和Web插件。
  - **面向对象**：插件通过继承基类 (`WidgetPlugin`, `ActionPlugin`, `SearchPlugin`) 来实现，结构清晰。
  - **自动发现**：插件放置在 `plugins` 目录中即可被自动加载。
  - **数据持久化**：每个插件都有自己的数据目录，通过 `get_data_dir()` 方法访问。
- **异步智能搜索**：
  - **即时搜索**：在主页的搜索框中输入，即可实时搜索所有可用的工具和来自搜索插件的内容。
  - **多源搜索**：同时从本地工具和所有已安装的搜索插件中获取结果。
  - **高级匹配**：支持忽略大小写、英文首字母、中文拼音及拼音首字母进行模糊搜索。
- **可扩展架构**：设计时充分考虑了可扩展性，开发者可以轻松地创建和分享自己的插件。

## 构建

要从源代码构建应用程序，请运行位于项目根目录下的 `build.ps1` 脚本。此脚本使用 `pyinstaller` 和 `main.spec` 文件来打包应用程序及其所有依赖项和资源。

```powershell
.\build.ps1
```

## 内置插件

### 界面插件 (Widget Plugins)

#### 1. 进制转换器
- **功能**：在二进制、十进制、十六进制之间进行实时转换。
- **特点**：在一个输入框中输入，其他进制的数值会立即更新。

#### 2. 颜色选择器
- **功能**：从调色板中选择颜色，并获取其 HEX、RGB 和 HSL 格式的值。
- **特点**：提供颜色预览，并自动调整文本颜色以确保可读性。

#### 3. 文件夹整理工具
- **功能**：根据文件的扩展名，将指定文件夹中的文件批量移动到按类别命名的子文件夹中。
- **特点**：分类规则（JSON格式）可由用户自定义并自动保存。

### 无界面插件 (Action Plugins)

#### 4. 快捷关机
- **功能**：提供一个一键关闭计算机的快捷操作。
- **特点**：执行前会弹出确认对话框，防止误操作。

### 搜索插件 (Search Plugins)

#### 5. 开始菜单搜索
- **功能**：搜索并启动 Windows 开始菜单中的所有应用程序（包括传统快捷方式和商店应用）。
- **特点**：通过 `Get-StartApps` 命令获取应用列表，使用 `AppID` 启动，兼容性好。

### Web插件 (Web Plugins)

#### 6. CyberChef
- **功能**：集成了强大的网络瑞士军刀 CyberChef 的本地版本。
- **用途**：用于数据转换、编码解码、加密解密等多种操作。

#### 7. Emoji
- **功能**：提供一个 Emoji 表情符号的搜索和复制工具。

## 技术栈

- **Python 3.13+**：项目的主要编程语言。
- **PySide6**：用于构建现代化用户界面的 GUI 框架。
- **pypinyin**：为搜索引擎提供中文拼音搜索能力。
- **模块化架构**：基于类的插件系统，易于扩展和维护。

## 插件开发指南

新的插件系统使用基于类的结构。要创建一个插件，你需要在 `plugins` 目录下创建一个新的文件夹，并在其中创建一个 `tool.py` 文件。

### 1. 界面插件 (WidgetPlugin)

这种插件会创建一个在标签页中显示的界面 (QWidget)。

**示例: `plugins/my_widget_plugin/tool.py`**
```python
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from plugin_system import WidgetPlugin, PluginType

class MyWidget(QWidget):
    def __init__(self, plugin_instance):
        super().__init__()
        # 访问插件实例，例如获取数据目录
        self.plugin = plugin_instance 
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("这是一个界面插件!"))

class MyWidgetPlugin(WidgetPlugin):
    def __init__(self, plugin_dir: str):
        super().__init__(plugin_dir)

    def get_name(self) -> str:
        return "我的界面插件"

    def get_description(self) -> str:
        return "一个插件示例，展示如何创建带UI的工具。"

    def get_type(self) -> PluginType:
        return PluginType.WIDGET

    def create_widget(self) -> QWidget:
        # 返回你的 QWidget 实例
        return MyWidget(self)
```

### 2. 无界面插件 (ActionPlugin)

这种插件没有界面，点击后会直接执行一个操作。

**示例: `plugins/my_action_plugin/tool.py`**
```python
from PySide6.QtWidgets import QMessageBox
from plugin_system import ActionPlugin, PluginType

class MyActionPlugin(ActionPlugin):
    def __init__(self, plugin_dir: str):
        super().__init__(plugin_dir)

    def get_name(self) -> str:
        return "我的快捷操作"

    def get_description(self) -> str:
        return "一个插件示例，点击后会弹出一个消息框。"

    def get_type(self) -> PluginType:
        return PluginType.ACTION

    def execute(self) -> None:
        # 在这里执行你的代码
        QMessageBox.information(None, "操作完成", "你点击了我的快捷操作！")
```

### 3. 搜索插件 (SearchPlugin)

这种插件可以为应用的主搜索框提供搜索结果。

**示例: `plugins/my_search_plugin/tool.py`**
```python
from typing import List
from plugin_system import SearchPlugin, PluginType, SearchResult

class MySearchPlugin(SearchPlugin):
    def __init__(self, plugin_dir: str):
        super().__init__(plugin_dir)

    def get_name(self) -> str:
        return "我的搜索插件"

    def get_description(self) -> str:
        return "一个插件示例，为应用提供搜索结果。"

    def get_type(self) -> PluginType:
        return PluginType.SEARCH

    def search(self, query: str) -> List[SearchResult]:
        # 根据查询返回结果列表
        if "hello" in query.lower():
            return [
                SearchResult(
                    title="你好世界",
                    description="这是一个来自'我的搜索插件'的结果",
                    plugin_name=self.get_name(),
                    data={"action": "greet"} # 自定义数据
                )
            ]
        return []

    def execute_result(self, result: SearchResult) -> None:
        # 当用户激活一个搜索结果时，执行此方法
        if result.data.get("action") == "greet":
            print("Hello World from search result!")
```

### 4. Web 插件 (WebPlugin)

Web 插件通过一个 `manifest.json` 文件来定义，它允许你将任何静态 Web 应用打包成一个插件。

**示例: `plugins/my_web_plugin/manifest.json`**
```json
{
    "name": "我的Web插件",
    "description": "一个Web插件示例。",
    "version": "1.0.0",
    "entry": "index.html",
    "author": "你的名字"
}
```
你需要将你的 Web 文件（`index.html` 等）和 `manifest.json` 一起放在 `plugins/my_web_plugin/` 目录下。

## 项目结构

```
python-toolbox/
├── main.py                    # 主程序入口
├── plugin_system.py           # 插件系统核心
├── search_engine.py           # 高级搜索引擎
├── pyproject.toml             # 项目配置文件
├── README.md                  # 项目说明文档
├── data/                      # 插件数据存储目录
│   └── plugins/
│       └── folder_organizer/
│           └── config.json
└── plugins/                   # 插件目录
    ├── base_converter/
    ├── color_picker/
    ├── folder_organizer/
    ├── quick_shutdown/
    ├── start_menu_search/
    ├── CyberChef/
    └── emoji/
```

## 安装和运行

### 环境要求

- Python 3.13 或更高版本
- `uv` 包管理器（推荐）

### 安装 `uv`

如果尚未安装 `uv`，请根据你的操作系统执行以下命令：

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装依赖

使用 `uv` 在项目中创建虚拟环境并安装依赖：

```bash
uv sync
```

### 运行应用

使用 `uv` 运行应用：

```bash
uv run python main.py
```

## 贡献

欢迎通过提交 Issue 和 Pull Request 来改进这个项目。

## 许可证

本项目采用开源许可证。