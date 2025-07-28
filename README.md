# Python 工具箱

一个基于 PySide6 的多标签页工具箱应用程序，支持可扩展的插件系统。

## 项目简介

Python 工具箱是一个桌面应用程序，提供了一个统一的界面来使用各种实用工具。应用程序采用插件架构，可以轻松添加新的工具功能。

## 主要功能

- **多标签页界面**：支持同时打开多个工具，每个工具在独立的标签页中运行
- **插件系统**：动态加载 `plugins` 目录下的工具插件
- **工具搜索**：在首页提供搜索功能，快速找到需要的工具
- **可扩展架构**：开发者可以轻松添加新的工具插件

## 内置工具

### 1. 进制转换器
- **功能**：在二进制、十进制、十六进制之间转换数字
- **特点**：实时转换，输入任意进制的数字，自动显示其他进制的对应值

### 2. 颜色选择器
- **功能**：从调色板中选择颜色并获取其不同格式的值
- **支持格式**：HEX、RGB、HSL
- **特点**：可视化颜色预览，自动调整文本颜色以确保对比度

### 3. CyberChef 集成
- **功能**：集成了 CyberChef 工具的本地版本
- **用途**：数据分析、编码解码、加密解密等

## 技术栈

- **Python 3.13+**
- **PySide6**：用于构建桌面GUI界面
- **插件架构**：基于动态模块加载

## 项目结构

```
test2/
├── main.py                 # 主应用程序入口
├── pyproject.toml          # 项目配置文件
├── plugins/                # 插件目录
│   ├── base_converter/     # 进制转换器插件
│   │   └── tool.py
│   ├── color_picker/       # 颜色选择器插件
│   │   └── tool.py
│   └── CyberChef/         # CyberChef 工具集成
│       ├── CyberChef_v10.19.4.html
│       └── ...
└── README.md              # 项目说明文档
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