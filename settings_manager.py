# settings_manager.py
import os
import json

class SettingsManager:
    """管理应用程序设置"""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = os.path.join(self.data_dir, "settings.json")

    def get_data_dir(self):
        """获取数据目录路径"""
        return self.data_dir

    def load_settings(self) -> dict:
        """加载设置文件"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    r = json.load(f)
                    print("load settings: ", r)
                    return r
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}")
        
        # 返回默认设置
        return {
            "hotkeys": {
                "show_window": "alt+space"
            }
        }

    def save_settings(self, settings: dict):
        """保存设置到文件"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def get_setting(self, key: str, default=None):
        """获取特定设置项"""
        settings = self.load_settings()
        r =  settings.get(key, default)
        print("get_setting: ", key, r)
        return r