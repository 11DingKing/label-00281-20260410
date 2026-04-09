"""
模型服务 - 单例模式管理 AI 模型实例

解决问题：
1. 避免全局变量管理模型
2. 确保多 Worker 环境下模型只加载一次（配合 preload_app=True）
3. 提供可测试的依赖注入接口
"""
import threading
import logging

logger = logging.getLogger('table_parser.model_service')


class ModelService:
    """
    AI 模型服务（线程安全单例）
    
    使用方式：
        model_service = ModelService.get_instance()
        result = model_service.table_extractor.extract(image_path)
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if ModelService._initialized:
            return
        
        self._table_detector = None
        self._structure_parser = None
        self._ocr_engine = None
        self._table_extractor = None
        self._models_loaded = False
        
        ModelService._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'ModelService':
        """获取单例实例"""
        return cls()
    
    @classmethod
    def reset_instance(cls):
        """重置实例（仅用于测试）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
    
    def initialize(self):
        """
        初始化所有模型
        
        在 Gunicorn 的 preload_app 模式下，此方法在 master 进程中调用，
        fork 后的 worker 进程共享已加载的模型内存（Copy-on-Write）
        """
        if self._models_loaded:
            logger.debug("模型已加载，跳过初始化")
            return
        
        with self._lock:
            if self._models_loaded:
                return
            
            logger.info("=" * 50)
            logger.info("开始加载 AI 模型...")
            logger.info("=" * 50)
            
            try:
                # 延迟导入，避免循环依赖
                from modules.table_detector import TableDetector
                from modules.structure_parser import StructureParser
                from modules.ocr_engine import OCREngine
                from modules.table_extractor import TableExtractor
                
                logger.info("[1/4] 加载表格检测模型 (YOLOv8)...")
                self._table_detector = TableDetector()
                
                logger.info("[2/4] 加载结构解析模型 (PubTabNet)...")
                self._structure_parser = StructureParser()
                
                logger.info("[3/4] 加载 OCR 引擎 (PaddleOCR)...")
                self._ocr_engine = OCREngine()
                
                logger.info("[4/4] 初始化表格提取器...")
                self._table_extractor = TableExtractor(
                    self._table_detector,
                    self._structure_parser,
                    self._ocr_engine
                )
                
                self._models_loaded = True
                logger.info("=" * 50)
                logger.info("所有模型加载完成！")
                logger.info("=" * 50)
                
            except Exception as e:
                logger.error(f"模型加载失败: {e}", exc_info=True)
                raise RuntimeError(f"模型初始化失败: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._models_loaded
    
    @property
    def table_detector(self):
        """获取表格检测器"""
        if not self._models_loaded:
            self.initialize()
        return self._table_detector
    
    @property
    def structure_parser(self):
        """获取结构解析器"""
        if not self._models_loaded:
            self.initialize()
        return self._structure_parser
    
    @property
    def ocr_engine(self):
        """获取 OCR 引擎"""
        if not self._models_loaded:
            self.initialize()
        return self._ocr_engine
    
    @property
    def table_extractor(self):
        """获取表格提取器"""
        if not self._models_loaded:
            self.initialize()
        return self._table_extractor
    
    def set_mock_models(self, table_detector=None, structure_parser=None, 
                        ocr_engine=None, table_extractor=None):
        """
        设置模拟模型（用于单元测试）
        
        Args:
            table_detector: Mock 的表格检测器
            structure_parser: Mock 的结构解析器
            ocr_engine: Mock 的 OCR 引擎
            table_extractor: Mock 的表格提取器
        """
        if table_detector:
            self._table_detector = table_detector
        if structure_parser:
            self._structure_parser = structure_parser
        if ocr_engine:
            self._ocr_engine = ocr_engine
        if table_extractor:
            self._table_extractor = table_extractor
        
        if any([table_detector, structure_parser, ocr_engine, table_extractor]):
            self._models_loaded = True
