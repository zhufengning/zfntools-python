# zfnbox - 开发指南

本文档面向希望参与 zfnbox项目开发的开发者，详细介绍项目的架构、代码结构和开发流程。

## 项目架构概览

zfnbox是一个基于 PySide6 的桌面应用程序，采用模块化设计，核心架构包括：

- **主程序入口** (`main.py`)：负责应用程序启动和单例管理
- **主窗口系统** (`main_window.py`)：提供用户界面和事件分发
- **插件系统** (`plugin_system.py`, `plugin_manager.py`)：支持多种类型插件的加载和管理
- **搜索引擎** (`search_engine.py`, `search_manager.py`)：提供智能搜索功能
- **系统托盘** (`tray_manager.py`)：管理系统托盘图标和菜单
- **UDP监听** (`udp_listener.py`)：实现窗口唤醒功能
- **设置管理** (`settings_manager.py`)：处理应用程序配置
- **异步搜索** (`search_workers.py`)：后台搜索工作器

### 重构说明

项目已经进行了大规模重构，将原本 473 行的 `main_window.py` 拆分为多个职责清晰的模块：

- **`main_window.py`** (176行) - 简化后的主窗口，只负责UI组装和事件分发
- **`tray_manager.py`** (68行) - 系统托盘管理
- **`udp_listener.py`** (52行) - UDP监听和窗口唤醒
- **`search_manager.py`** (184行) - 搜索管理（本地搜索、插件搜索、结果处理）
- **`plugin_manager.py`** (113行) - 插件管理（加载、执行、标签页管理）

这种设计遵循 **单一职责原则**，使得：
- 每个模块只负责一个特定功能
- 代码更易维护和理解
- 单元测试更容易编写
- 模块可以在其他项目中复用

## 核心文件详解

### 1. main.py - 应用程序入口

**作用**：应用程序的启动入口，负责单例管理和生命周期控制。

**核心功能**：
- **单例检测**：通过 `.port` 文件实现单例模式，防止重复启动
- **实例唤醒**：当检测到已有实例时，通过 UDP 消息唤醒现有窗口
- **资源清理**：使用 `try...finally` 确保程序退出时清理 `.port` 文件

**关键函数**：
- `check_and_wake_instance()`: 检查并唤醒已存在的实例
- `main()`: 主函数，处理应用程序生命周期

**技术要点**：
- 使用 UDP Socket 进行进程间通信
- 异常安全的资源清理机制
- 优雅的程序退出处理

### 2. main_window.py - 主窗口系统（重构后）

**作用**：应用程序的主界面，负责UI组装和事件分发。

**核心职责**：
- 初始化各个管理器（托盘、UDP、搜索、插件）
- 设置主窗口UI（标签页、搜索框、工具列表）
- 处理键盘事件（上下箭头、回车、ESC）
- 分发事件给对应的管理器

**关键方法**：
- `setup_home_tab()`: 设置首页标签
- `show_and_raise()`: 显示窗口并置于顶层
- `handle_item_activation()`: 处理项目激活（双击）
- `close_tab()`: 关闭标签页

**重构优势**：
- 从 473 行减少到 176 行
- 职责单一，只负责UI和事件分发
- 不再直接处理插件、搜索、托盘等逻辑

### 3. tray_manager.py - 系统托盘管理器

**作用**：管理系统托盘图标和菜单。

**核心功能**：
- 创建和配置托盘图标
- 创建托盘菜单（显示/隐藏、退出）
- 处理托盘图标点击事件
- 切换窗口可见性

**关键方法**：
- `_create_menu()`: 创建托盘菜单
- `toggle_window_visibility()`: 切换窗口显示/隐藏

### 4. udp_listener.py - UDP监听器

**作用**：UDP监听和窗口唤醒功能。

**核心功能**：
- 绑定随机UDP端口
- 将端口号写入 `.port` 文件
- 监听UDP消息
- 收到消息时唤醒窗口
- 清理端口文件

**关键方法**：
- `_init_socket()`: 初始化UDP套接字
- `_handle_message()`: 处理收到的UDP消息
- `cleanup_port_file()`: 清理端口文件（静态方法）

### 5. search_manager.py - 搜索管理器

**作用**：管理所有搜索相关功能。

**核心功能**：
- 初始化搜索引擎
- 管理搜索防抖定时器
- 启动本地搜索（搜索本地插件）
- 启动插件搜索（调用搜索插件）
- 管理搜索线程和工作器
- 处理搜索结果并显示在列表中

**关键方法**：
- `start_search()`: 开始异步搜索
- `stop_all_searches()`: 停止所有搜索
- `add_plugin_to_list()`: 将插件添加到列表
- `update_tool_list()`: 显示所有插件

### 6. plugin_manager.py - 插件管理器

**作用**：管理插件加载和执行。

**核心功能**：
- 加载所有插件
- 打开不同类型的插件（Widget/Action/Web）
- 管理插件标签页
- 确保标签名唯一
- 执行搜索结果

**关键方法**：
- `load_plugins()`: 加载所有插件
- `open_plugin()`: 打开插件
- `execute_search_result()`: 执行搜索结果
- `_get_unique_tab_name()`: 获取唯一标签名

### 7. plugin_system.py - 插件系统核心

**作用**：定义插件架构，提供插件加载和管理功能。

**核心类**：

#### 插件类型枚举
```python
class PluginType(Enum):
    WIDGET = "widget"    # 界面插件
    ACTION = "action"    # 无界面插件
    SEARCH = "search"    # 搜索插件
    WEB = "web"         # Web插件
```

#### 插件基类
- **BasePlugin**：所有插件的抽象基类
- **WidgetPlugin**：界面插件基类，需实现 `create_widget()` 方法
- **ActionPlugin**：无界面插件基类，需实现 `execute()` 方法
- **SearchPlugin**：搜索插件基类，需实现 `search()` 和 `execute_result()` 方法
- **WebPlugin**：Web插件类，基于 manifest.json 配置

#### 插件加载器
- **PluginLoader**：负责扫描和加载插件
- **动态加载**：使用 `importlib` 动态加载 Python 模块
- **类型识别**：根据文件类型（tool.py 或 manifest.json）识别插件类型
- **错误处理**：提供完善的插件加载错误处理

**技术要点**：
- 使用抽象基类确保插件接口一致性
- 动态模块加载和类实例化
- 插件数据目录管理
- 搜索结果封装和处理

### 8. search_engine.py - 智能搜索引擎

**作用**：提供高级搜索功能，支持多种匹配算法。

**核心功能**：

#### 搜索项目管理
- **SearchableItem**：可搜索项目的数据结构
- **批量管理**：支持添加、清空搜索项目

#### 智能匹配算法
1. **完全匹配**：忽略大小写的精确匹配（权重 1.0）
2. **包含匹配**：子字符串匹配（权重 0.8）
3. **首字母匹配**：英文单词首字母缩写匹配
4. **拼音匹配**：中文拼音和拼音首字母匹配（需要 pypinyin）
5. **模糊匹配**：基于编辑距离的模糊匹配

#### 评分系统
- **多字段搜索**：标题、描述、关键词分别搜索
- **权重计算**：不同字段使用不同权重
- **结果排序**：按相关度分数排序

**技术要点**：
- 可选依赖处理（pypinyin）
- 多种匹配算法的组合使用
- 性能优化的搜索实现

### 9. search_workers.py - 异步搜索工作器

**作用**：提供后台搜索功能，避免界面阻塞。

**核心类**：
- **SearchWorker**：插件搜索工作器，在后台执行插件搜索
- **LocalSearchWorker**：本地搜索工作器，搜索本地插件

**技术要点**：
- 基于 `QObject` 和信号槽机制
- 线程安全的搜索执行
- 异常处理和错误报告

### 10. settings_manager.py - 设置管理器

**作用**：管理应用程序配置和用户设置。

**核心功能**：
- **JSON 配置**：使用 JSON 格式存储设置
- **默认设置**：提供默认配置值
- **数据目录管理**：管理应用程序数据目录
- **错误处理**：处理配置文件读写错误

## 项目配置文件

### pyproject.toml - 项目配置

定义项目元数据、依赖关系和构建配置：

```toml
[project]
name = "python-toolbox"
version = "0.2.0"
requires-python = ">=3.13"
dependencies = [
    "PySide6",           # GUI框架
    "pypinyin",          # 中文拼音搜索
    "pynput",            # 输入处理
    "nuitka>=2.7.13",    # 编译器
    "pyinstaller>=6.15.0", # 打包工具
    "global-hotkeys",    # 全局热键
]
```

### build.ps1 - 构建脚本

简单的 PowerShell 脚本，使用 PyInstaller 打包应用程序：
```powershell
pyinstaller main.spec --noconfirm
```

## 数据流和交互模式

### 1. 应用程序启动流程（重构后）

```
main.py
├── check_and_wake_instance() - 检查单例
├── QApplication() - 创建应用程序
├── MainWindow() - 创建主窗口
│   ├── SettingsManager() - 初始化设置管理器
│   ├── setup_home_tab() - 设置首页UI
│   ├── PluginManager() - 初始化插件管理器
│   │   └── load_plugins() - 加载所有插件
│   ├── SearchManager() - 初始化搜索管理器
│   │   └── setup_search_engine() - 设置搜索引擎
│   ├── TrayManager() - 初始化托盘管理器
│   └── UdpListener() - 初始化UDP监听器
└── app.exec() - 启动事件循环
```

### 2. 搜索流程（重构后）

```
用户输入 → search_bar (MainWindow)
├── on_search_text_changed() - 主窗口接收输入
├── SearchManager.on_search_text_changed() - 搜索管理器处理
│   └── 防抖定时器 (300ms)
├── MainWindow.start_async_search() - 主窗口触发搜索
├── SearchManager.start_search() - 搜索管理器执行
│   ├── _start_local_search() - 本地搜索
│   │   └── LocalSearchWorker.run() - 后台执行
│   └── _start_plugin_search() - 插件搜索
│       └── SearchWorker.run() - 后台执行
└── SearchManager.add_plugin_to_list() - 显示结果
```

### 3. 插件加载流程（重构后）

```
PluginManager.__init__()
├── load_plugins()
│   └── PluginLoader.load_plugins()
│       ├── 扫描 plugins/ 目录
│       ├── 对每个子目录：
│       │   ├── 检查 manifest.json → WebPlugin
│       │   ├── 检查 tool.py → Python插件
│       │   │   ├── 动态加载模块
│       │   │   ├── 检查 PLUGIN_TYPE
│       │   │   └── 创建对应插件实例
│       │   └── 错误处理和日志记录
│       └── 返回插件列表
└── 存储插件列表

PluginManager.open_plugin()
├── 判断插件类型
├── WidgetPlugin → _open_widget_plugin()
├── ActionPlugin → _execute_action_plugin()
└── WebPlugin → _open_web_plugin()
```

## 开发环境设置

### 依赖管理

项目使用 `uv` 作为包管理器：

```bash
# 安装依赖
uv sync

# 运行应用程序
uv run python main.py

# 添加新依赖
uv add package_name
```

## 代码规范

### 命名约定

- **类名**: PascalCase (如 `MainWindow`, `PluginLoader`)
- **函数名**: snake_case (如 `load_plugins`, `start_search`)
- **常量**: UPPER_SNAKE_CASE (如 `PORT_FILE`, `PLUGIN_TYPE`)
- **私有方法**: 以下划线开头 (如 `_calculate_score`)

### 文档字符串

使用简洁的中文文档字符串：

```python
def load_plugins(self):
    """加载所有插件"""
    pass

def _calculate_score(self, query: str, item: SearchableItem) -> float:
    """计算搜索相关度分数"""
    pass
```

### 错误处理

- 使用具体的异常类型
- 提供有意义的错误消息
- 在关键位置添加 try-except 块
- 使用日志记录错误信息

```python
try:
    with open(port_file, "r") as f:
        port = int(f.read().strip())
except (IOError, ValueError) as e:
    print(f"Error reading port file: {e}")
    return False
```

## 测试策略

### 单元测试

为核心组件编写单元测试：

- **搜索引擎**: 测试各种匹配算法
- **插件加载器**: 测试插件发现和加载
- **设置管理器**: 测试配置读写

### 集成测试

测试组件间的交互：

- **主窗口与插件系统**: 测试插件加载和执行
- **搜索系统**: 测试异步搜索流程
- **UDP通信**: 测试单例和唤醒功能

### 手动测试

- **用户界面**: 测试所有交互功能
- **插件兼容性**: 测试各种类型插件
- **性能测试**: 测试大量插件和搜索结果的性能

## 性能优化

### 搜索性能

- **异步搜索**: 避免界面阻塞
- **搜索缓存**: 缓存搜索结果
- **延迟搜索**: 使用定时器避免频繁搜索
- **结果限制**: 限制搜索结果数量

### 内存管理

- **插件懒加载**: 按需加载插件资源
- **线程清理**: 及时清理搜索线程
- **缓存管理**: 合理管理搜索缓存

### 启动优化

- **并行加载**: 并行加载插件
- **延迟初始化**: 延迟非关键组件初始化
- **资源预加载**: 预加载常用资源

## 调试技巧

### 日志记录

在关键位置添加调试信息：

```python
print(f"Loading plugin: {plugin_name}")
print(f"Search query: {query}, results: {len(results)}")
```

### 异常追踪

使用详细的异常信息：

```python
except Exception as e:
    print(f"Error in {self.__class__.__name__}: {e}")
    import traceback
    traceback.print_exc()
```


## 常见问题

### Q: 如何添加新的搜索算法？

A: 在 `search_engine.py` 的 `_match_text()` 方法中添加新的匹配逻辑，并调整权重。

### Q: 如何优化插件加载性能？

A: 考虑实现插件懒加载，只在需要时才完全初始化插件。

### Q: 如何处理插件加载错误？

A: 在 `PluginLoader` 中添加更详细的错误处理和日志记录，确保单个插件错误不影响整体功能。

### Q: 如何扩展搜索功能？

A: 可以在 `SearchEngine` 中添加新的匹配算法，或在 `MainWindow` 中添加新的搜索源。
