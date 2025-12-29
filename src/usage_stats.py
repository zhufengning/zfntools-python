
import os
import json
from typing import List, Dict, Any, Optional

class UsageStatsManager:
    """统计和管理搜索项的使用频率"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.stats_file = os.path.join(self.data_dir, "usage_stats.json")
        self.stats = self._load_stats()
        
    def _load_stats(self) -> Dict:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading usage stats: {e}")
        return {}
        
    def _save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving usage stats: {e}")
            
    def _get_item_key(self, item_type: str, item_id: str) -> str:
        """生成唯一键"""
        return f"{item_type}:{item_id}"
        
    def record_usage(self, item_type: str, item_id: str, item_data: Dict[str, Any]):
        """记录一次使用"""
        key = self._get_item_key(item_type, item_id)
        
        if key not in self.stats:
            self.stats[key] = {
                "type": item_type,
                "id": item_id,
                "count": 0,
                "data": item_data,  # 存储完整数据以便重建
                "last_used": 0
            }
            
        self.stats[key]["count"] += 1
        import time
        self.stats[key]["last_used"] = time.time()
        self._save_stats()
        print(f"[UsageStats] Recorded usage for {key}, count: {self.stats[key]['count']}")
        
    def get_top_items(self, limit: int = 3) -> List[Dict[str, Any]]:
        """获取使用频率最高的项目"""
        if not self.stats:
            return []
            
        # 按使用次数降序排序
        sorted_items = sorted(
            self.stats.values(), 
            key=lambda x: x.get("count", 0), 
            reverse=True
        )
        
        return sorted_items[:limit]
