"""
OCR引擎模块 - 使用 PaddleOCR 进行文字识别
支持中英文混合识别
"""
import os
import cv2
import logging
import threading

logger = logging.getLogger('table_parser.ocr')


class OCREngine:
    # 类级别的锁，保护模型推理（PaddleOCR 不是线程安全的）
    _inference_lock = threading.Lock()
    
    def __init__(self, lang=None):
        """
        初始化 PaddleOCR 引擎
        
        Args:
            lang: 语言，'ch' 中英文，'en' 英文，默认从环境变量读取
        """
        self.lang = lang or os.getenv('OCR_LANG', 'ch')
        self.ocr = None
        
        try:
            logger.info(f"初始化 PaddleOCR 引擎 (语言: {self.lang})...")
            from paddleocr import PaddleOCR
            
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=False,
                show_log=False
            )
            logger.info("PaddleOCR 引擎初始化成功")
                
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {e}")
            self.ocr = None
    
    def recognize(self, image, bbox=None):
        """
        识别图像中的文字
        
        Args:
            image: 图像路径或 numpy 数组
            bbox: 可选的裁剪区域 [x1, y1, x2, y2]
            
        Returns:
            str: 识别的文字
        """
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图像文件不存在: {image}")
            image = cv2.imread(image)
        
        if image is None:
            raise ValueError("无法读取图像")
        
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = image.shape[:2]
            x1 = max(0, min(int(x1), w))
            y1 = max(0, min(int(y1), h))
            x2 = max(0, min(int(x2), w))
            y2 = max(0, min(int(y2), h))
            image = image[y1:y2, x1:x2]
        
        if self.ocr is not None:
            try:
                # 使用锁保护模型推理
                with self._inference_lock:
                    results = self.ocr.ocr(image, cls=True)
                if results and results[0]:
                    texts = [line[1][0] for line in results[0]]
                    return ' '.join(texts).strip()
            except Exception as e:
                logger.debug(f"OCR 识别异常: {e}")
        
        return ""
    
    def recognize_with_positions(self, image):
        """
        识别图像中的文字并返回位置信息
        
        Args:
            image: 图像路径或 numpy 数组
            
        Returns:
            list: 包含文字和位置信息的列表
        """
        if isinstance(image, str):
            image = cv2.imread(image)
        
        if image is None:
            return []
        
        results = []
        
        if self.ocr is not None:
            try:
                # 使用锁保护模型推理
                with self._inference_lock:
                    ocr_results = self.ocr.ocr(image, cls=False)
                
                if ocr_results and ocr_results[0]:
                    for line in ocr_results[0]:
                        bbox = line[0]
                        text = line[1][0]
                        confidence = line[1][1]
                        
                        if text.strip():
                            x_coords = [p[0] for p in bbox]
                            y_coords = [p[1] for p in bbox]
                            
                            x_min = min(x_coords)
                            x_max = max(x_coords)
                            y_min = min(y_coords)
                            y_max = max(y_coords)
                            
                            results.append({
                                'text': text,
                                'x': (x_min + x_max) / 2,
                                'y': (y_min + y_max) / 2,
                                'x_min': float(x_min),
                                'x_max': float(x_max),
                                'y_min': float(y_min),
                                'y_max': float(y_max),
                                'confidence': float(confidence)
                            })
                            
                    logger.debug(f"OCR 识别到 {len(results)} 个文字区域")
                    
            except Exception as e:
                logger.error(f"PaddleOCR 识别失败: {e}")
        
        return results
