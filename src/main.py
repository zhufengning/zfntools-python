import os
import sys
import socket
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def check_and_wake_instance():
    port_file = ".port"
    if not os.path.exists(port_file):
        return False

    try:
        with open(port_file, "r") as f:
            port = int(f.read().strip())
        
        # Send a UDP message to wake up the existing instance
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(b"wake", ("127.0.0.1", port))
        return True
    except (IOError, ValueError) as e:
        print(f"Error reading port file, proceeding to start new instance: {e}")
        try:
            os.remove(port_file)
        except OSError:
            pass
        return False

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", action="store_true", help="Start in system tray without showing window")
    args, _ = parser.parse_known_args()

    if check_and_wake_instance():
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    main_window = MainWindow()
    
    if not args.silent:
        main_window.show_and_raise()
    
    port_file = ".port"

    try:
        # Start the application event loop
        exit_code = app.exec()
    finally:
        # This cleanup will run on normal exit and on most unhandled exceptions
        if os.path.exists(port_file):
            try:
                os.remove(port_file)
            except OSError as e:
                print(f"Error removing port file on exit: {e}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
