
import os
import json
from typing import List, Dict, Any

class UsageStatsManager:
    """统计和管理搜索项的使用频率"""

    STATS_VERSION = 2
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.stats_file = os.path.join(self.data_dir, "usage_stats.json")
        self.stats = self._load_stats()

    @staticmethod
    def normalize_query(query: str) -> str:
        return " ".join((query or "").strip().lower().split())

    @staticmethod
    def make_item_key(item_type: str, item_id: str) -> str:
        return f"{item_type}:{item_id}"

    def _new_stats(self) -> Dict[str, Any]:
        return {"version": self.STATS_VERSION, "queries": {}}

    def _delete_stats_file(self, reason: str) -> None:
        try:
            os.remove(self.stats_file)
            print(f"[UsageStats] Deleted invalid stats file ({reason}): {self.stats_file}")
        except FileNotFoundError:
            return
        except Exception as e:
            print(f"[UsageStats] Failed to delete invalid stats file: {e}")

    def _is_valid_stats(self, stats: Any) -> bool:
        if not isinstance(stats, dict):
            return False
        if stats.get("version") != self.STATS_VERSION:
            return False
        queries = stats.get("queries")
        if not isinstance(queries, dict):
            return False

        for query, items in queries.items():
            if not isinstance(query, str):
                return False
            if not isinstance(items, dict):
                return False

            for item_key, record in items.items():
                if not isinstance(item_key, str):
                    return False
                if not isinstance(record, dict):
                    return False

                item_type = record.get("type")
                item_id = record.get("id")
                count = record.get("count")
                if not isinstance(item_type, str) or not isinstance(item_id, str):
                    return False
                if not isinstance(count, int):
                    return False
                if item_key != self.make_item_key(item_type, item_id):
                    return False

        return True
        
    def _load_stats(self) -> Dict:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                if not self._is_valid_stats(stats):
                    self._delete_stats_file("invalid format")
                    return self._new_stats()
                return stats
            except Exception as e:
                print(f"Error loading usage stats: {e}")
                self._delete_stats_file("load error")
                return self._new_stats()
        return self._new_stats()
        
    def _save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving usage stats: {e}")

    def record_usage(self, query: str, item_type: str, item_id: str, item_data: Dict[str, Any]):
        """记录一次使用"""
        normalized_query = self.normalize_query(query)
        key = self.make_item_key(item_type, item_id)

        query_stats = self.stats["queries"].setdefault(normalized_query, {})
        if key not in query_stats:
            query_stats[key] = {
                "type": item_type,
                "id": item_id,
                "count": 0,
                "data": item_data,
                "last_used": 0,
            }

        query_stats[key]["count"] += 1
        import time
        query_stats[key]["last_used"] = time.time()
        self._save_stats()
        print(f"[UsageStats] Recorded usage for query='{normalized_query}' {key}, count: {query_stats[key]['count']}")
        
    def get_top_items(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取使用频率最高的项目"""
        normalized_query = self.normalize_query(query)
        items = self.stats.get("queries", {}).get(normalized_query, {})
        if not items:
            return []
            
        # 按使用次数降序排序
        sorted_items = sorted(
            items.values(),
            key=lambda x: (x.get("count", 0), x.get("last_used", 0)),
            reverse=True
        )
        
        return sorted_items[:limit]
