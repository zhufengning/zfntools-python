# search_engine.py

import re
from typing import List, Tuple, Any
from dataclasses import dataclass

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False
    print("Warning: pypinyin not installed. Chinese pinyin search will be disabled.")

@dataclass
class SearchableItem:
    """可搜索的项目"""
    title: str
    description: str = ""
    data: Any = None
    keywords: List[str] = None  # 额外的关键词

class SearchEngine:
    """高级搜索引擎"""
    
    def __init__(self):
        self.items: List[SearchableItem] = []
    
    def add_item(self, item: SearchableItem):
        """添加可搜索项目"""
        self.items.append(item)
    
    def add_items(self, items: List[SearchableItem]):
        """批量添加可搜索项目"""
        self.items.extend(items)
    
    def clear(self):
        """清空所有项目"""
        self.items.clear()
    
    def search(self, query: str, max_results: int = 50) -> List[Tuple[SearchableItem, float]]:
        """搜索项目，返回匹配的项目和相关度分数"""
        if not query.strip():
            return [(item, 1.0) for item in self.items[:max_results]]
        
        query = query.strip()
        results = []
        
        for item in self.items:
            score = self._calculate_score(query, item)
            if score > 0:
                results.append((item, score))
        
        # 按相关度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]
    
    def _calculate_score(self, query: str, item: SearchableItem) -> float:
        """计算搜索相关度分数"""
        max_score = 0.0
        
        # 搜索标题
        title_score = self._match_text(query, item.title)
        max_score = max(max_score, title_score * 1.0)  # 标题权重最高
        
        # 搜索描述
        if item.description:
            desc_score = self._match_text(query, item.description)
            max_score = max(max_score, desc_score * 0.8)  # 描述权重稍低
        
        # 搜索关键词
        if item.keywords:
            for keyword in item.keywords:
                keyword_score = self._match_text(query, keyword)
                max_score = max(max_score, keyword_score * 0.9)  # 关键词权重中等
        
        return max_score
    
    def _match_text(self, query: str, text: str) -> float:
        """匹配文本，返回匹配分数"""
        if not text:
            return 0.0
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        # 1. 完全匹配（忽略大小写）
        if query_lower == text_lower:
            return 1.0
        
        # 2. 包含匹配（忽略大小写）
        if query_lower in text_lower:
            return 0.8
        
        # 3. 英文首字母匹配
        acronym_score = self._match_acronym(query, text)
        if acronym_score > 0:
            return acronym_score
        
        # 4. 中文拼音匹配
        if PYPINYIN_AVAILABLE:
            pinyin_score = self._match_pinyin(query, text)
            if pinyin_score > 0:
                return pinyin_score
        
        # 5. 模糊匹配（部分字符匹配）
        fuzzy_score = self._fuzzy_match(query_lower, text_lower)
        return fuzzy_score
    
    def _match_acronym(self, query: str, text: str) -> float:
        """英文首字母匹配"""
        # 提取英文单词首字母
        words = re.findall(r'\b[a-zA-Z]+', text)
        if not words:
            return 0.0
        
        acronym = ''.join(word[0].lower() for word in words)
        query_lower = query.lower()
        
        if query_lower == acronym:
            return 0.7
        elif query_lower in acronym:
            return 0.5
        
        return 0.0
    
    def _match_pinyin(self, query: str, text: str) -> float:
        """中文拼音匹配"""
        if not PYPINYIN_AVAILABLE:
            return 0.0
        
        # 提取中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        if not chinese_chars:
            return 0.0
        
        chinese_text = ''.join(chinese_chars)
        
        # 完整拼音匹配
        pinyin_full = ''.join(lazy_pinyin(chinese_text, style=Style.NORMAL))
        query_lower = query.lower()
        
        if query_lower == pinyin_full:
            return 0.6
        elif query_lower in pinyin_full:
            return 0.4
        
        # 拼音首字母匹配
        pinyin_initials = ''.join(lazy_pinyin(chinese_text, style=Style.FIRST_LETTER))
        if query_lower == pinyin_initials:
            return 0.5
        elif query_lower in pinyin_initials:
            return 0.3
        
        return 0.0
    
    def _fuzzy_match(self, query: str, text: str) -> float:
        """模糊匹配"""
        if len(query) < 2:
            return 0.0
        
        # 计算字符匹配度
        matches = 0
        for char in query:
            if char in text:
                matches += 1
        
        if matches == 0:
            return 0.0
        
        # 匹配度 = 匹配字符数 / 查询长度
        match_ratio = matches / len(query)
        
        # 只有匹配度超过50%才认为是有效匹配
        if match_ratio >= 0.5:
            return match_ratio * 0.2  # 模糊匹配分数较低
        
        return 0.0

# 全局搜索引擎实例
global_search_engine = SearchEngine()

def get_search_engine() -> SearchEngine:
    """获取全局搜索引擎实例"""
    return global_search_engine