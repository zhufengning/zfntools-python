import sys
import os
import socket
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

PORT_FILE = ".port"

def check_and_wake_instance():
    """
    通过检查 .port 文件来确认实例是否已在运行。
    如果是，则发送 UDP 消息以唤醒它，并返回 True。
    否则，返回 False。
    """
    if os.path.exists(PORT_FILE):
        try:
            with open(PORT_FILE, "r") as f:
                port_str = f.read().strip()
                if port_str.isdigit():
                    port = int(port_str)
                    # 通过 UDP 发送唤醒消息
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(b"wake", ("127.0.0.1", port))
                    return True
        except (IOError, ValueError) as e:
            print(f"读取端口文件错误: {e}")
            # 如果文件无效，尝试删除它
            try:
                os.remove(PORT_FILE)
            except OSError:
                pass
    return False

def main():
    """应用程序主函数"""
    if check_and_wake_instance():
        print("应用程序已在运行，正在唤醒。")
        sys.exit(0)

    # 创建应用程序
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
