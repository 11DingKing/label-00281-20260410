"""
历史记录服务

管理解析历史的持久化和查询
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger('table_parser.history_service')


class HistoryService:
    """历史记录服务"""
    
    def __init__(self, history_folder: str, results_folder: str, max_records: int = 100):
        """
        初始化历史记录服务
        
        Args:
            history_folder: 历史记录存储目录
            results_folder: 解析结果存储目录
            max_records: 最大保留记录数
        """
        self.history_folder = history_folder
        self.results_folder = results_folder
        self.max_records = max_records
        self.history_file = os.path.join(history_folder, 'history.json')
        
        # 确保目录存在
        os.makedirs(history_folder, exist_ok=True)
    
    def load(self) -> List[Dict]:
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载历史记录失败: {e}")
        return []
    
    def save(self, history: List[Dict]) -> None:
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"保存历史记录失败: {e}")
            raise
    
    def add(self, record: Dict) -> Dict:
        """
        添加历史记录
        
        Args:
            record: 记录数据（不含 id 和 created_at）
            
        Returns:
            完整的记录数据（含 id 和 created_at）
        """
        history = self.load()
        
        # 添加元数据
        record['id'] = str(uuid.uuid4())
        record['created_at'] = datetime.now().isoformat()
        
        # 插入到列表开头
        history.insert(0, record)
        
        # 保留最近 N 条记录
        history = history[:self.max_records]
        
        self.save(history)
        logger.info(f"添加历史记录: {record['id']}")
        
        return record
    
    def get(self, record_id: str) -> Optional[Dict]:
        """
        获取单条历史记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            记录数据，如果不存在则返回 None
        """
        history = self.load()
        for record in history:
            if record.get('id') == record_id:
                return record
        return None
    
    def get_with_result(self, record_id: str) -> Optional[Dict]:
        """
        获取历史记录及其关联的解析结果
        
        Args:
            record_id: 记录 ID
            
        Returns:
            记录数据（含 result 字段），如果不存在则返回 None
        """
        record = self.get(record_id)
        if not record:
            return None
        
        # 加载关联的结果文件
        result_file = record.get('result_file')
        if result_file:
            result_path = os.path.join(self.results_folder, result_file)
            if os.path.exists(result_path):
                try:
                    with open(result_path, 'r', encoding='utf-8') as f:
                        record['result'] = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"加载结果文件失败: {e}")
        
        return record
    
    def delete(self, record_id: str) -> bool:
        """
        删除历史记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否删除成功
        """
        history = self.load()
        original_length = len(history)
        history = [r for r in history if r.get('id') != record_id]
        
        if len(history) == original_length:
            return False
        
        self.save(history)
        logger.info(f"删除历史记录: {record_id}")
        return True
    
    def clear(self) -> int:
        """
        清空历史记录
        
        Returns:
            被删除的记录数
        """
        history = self.load()
        count = len(history)
        self.save([])
        logger.info(f"清空历史记录，共删除 {count} 条")
        return count
    
    def list(self, page: int = 1, per_page: int = 20) -> Dict:
        """
        分页获取历史记录列表
        
        Args:
            page: 页码（从 1 开始）
            per_page: 每页数量
            
        Returns:
            包含分页信息的字典
        """
        history = self.load()
        total = len(history)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'history': history[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
