# udp_listener.py
import os
from PySide6.QtNetwork import QUdpSocket, QHostAddress

PORT_FILE = ".port"


class UdpListener:
    """UDP监听器，用于唤醒窗口"""
    
    def __init__(self, parent):
        """
        初始化UDP监听器
        
        Args:
            parent: 父窗口对象
        """
        self.parent = parent
        self.udp_socket = QUdpSocket(parent)
        self._init_socket()
    
    def _init_socket(self):
        """初始化UDP套接字"""
        # 绑定到任意可用端口
        if self.udp_socket.bind(QHostAddress.LocalHost, 0):
            port = self.udp_socket.localPort()
            self._write_port_file(port)
            self.udp_socket.readyRead.connect(self._handle_message)
        else:
            print("Error: Unable to bind to UDP socket.")
    
    def _write_port_file(self, port: int):
        """将端口号写入文件"""
        try:
            with open(PORT_FILE, "w") as f:
                f.write(str(port))
        except IOError as e:
            print(f"Error writing port file: {e}")
    
    def _handle_message(self):
        """处理收到的UDP消息"""
        while self.udp_socket.hasPendingDatagrams():
            datagram = self.udp_socket.receiveDatagram()
            message = datagram.data().data().decode('utf-8', errors='ignore').strip()
            
            if message == "wake":
                # 唤醒主界面
                self.parent.show_and_raise()
            elif message == "quit":
                # 退出应用程序
                self.parent.exit_application()
    
    @staticmethod
    def cleanup_port_file():
        """清理端口文件"""
        if os.path.exists(PORT_FILE):
            try:
                os.remove(PORT_FILE)
            except OSError as e:
                print(f"Error removing port file: {e}")
