# main.py
import sys
import os
import locale
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSharedMemory
from PySide6.QtNetwork import QLocalSocket
from main_window import MainWindow

def check_single_instance():
    """检查是否已有实例在运行"""
    unique_key = "python-toolbox-unique-key"
    socket = QLocalSocket()
    socket.connectToServer(unique_key)
    
    if socket.waitForConnected(1000):
        # 已有实例在运行，发送信号并退出
        socket.write(b"show")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return False
    
    return True


def main():
    """应用程序主函数"""
    # 设置编码
    try:
        # 获取系统默认编码
        default_locale = locale.getdefaultlocale()
        print(f"System locale: {default_locale}")
    except Exception as e:
        print(f"获取系统编码失败: {e}")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # 单例检测
    unique_key = "python-toolbox-unique-key"
    shared_mem = QSharedMemory(unique_key)

    # 尝试创建共享内存段
    if not shared_mem.create(1):
        # 如果创建失败，检查是否是因为已存在
        if shared_mem.error() == QSharedMemory.SharedMemoryError.AlreadyExists:
            # 确实是已存在，说明有实例在运行
            # 连接到本地服务并发送消息以显示窗口
            if check_single_instance():
                print("应用程序已在运行")
            sys.exit(0)
        else:
            # 其他错误，无法创建共享内存
            print(f"无法创建共享内存段: {shared_mem.errorString()}")
            sys.exit(1)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 确保在程序退出时分离共享内存
    app.aboutToQuit.connect(shared_mem.detach)
    
    # 运行应用程序
    sys.exit(app.exec())




if __name__ == "__main__":
    main()
