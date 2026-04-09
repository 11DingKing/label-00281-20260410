"""
表格检测模块 - 使用 YOLOv8 进行表格检测

模型说明:
- 优先使用专用表格检测模型 (keremberke/yolov8m-table-extraction)
- 该模型在表格检测数据集上训练，可检测 'table' 和 'table rotated' 类别
- 如果专用模型不可用，回退到通用 YOLOv8 模型或基于图像处理的备用方法
"""
import cv2
import numpy as np
from ultralytics import YOLO
import os
import logging

logger = logging.getLogger('table_parser.detector')


class TableDetector:
    def __init__(self, model_path=None):
        """
        初始化表格检测器
        
        Args:
            model_path: YOLO模型路径，如果为None则尝试加载专用表格检测模型
        """
        self.model = None
        self.model_path = model_path
        
        # 尝试加载模型的优先级列表
        models_to_try = []
        
        if model_path:
            models_to_try.append(model_path)
        
        # 从环境变量获取模型配置
        env_model = os.getenv('YOLO_MODEL', 'keremberke/yolov8m-table-extraction')
        models_to_try.extend([
            env_model,
            'keremberke/yolov8m-table-extraction',
            'keremberke/yolov8s-table-extraction',
            'yolov8n.pt'
        ])
        
        # 去重
        models_to_try = list(dict.fromkeys(models_to_try))
        
        for model_name in models_to_try:
            try:
                logger.info(f"尝试加载模型: {model_name}")
                self.model = YOLO(model_name)
                self.model_path = model_name
                logger.info(f"YOLOv8 模型加载成功: {model_name}")
                if hasattr(self.model, 'names'):
                    logger.debug(f"模型类别: {self.model.names}")
                break
            except Exception as e:
                logger.warning(f"加载 {model_name} 失败: {e}")
                continue
        
        if self.model is None:
            logger.warning("所有模型加载失败，将使用备用检测方法")
    
    def detect(self, image_path):
        """
        检测图像中的表格
        
        Args:
            image_path: 图像路径
            
        Returns:
            list: 检测到的表格边界框列表，格式为 [[x1, y1, x2, y2, confidence], ...]
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 处理 PDF 文件
        actual_image_path = image_path
        if image_path.lower().endswith('.pdf'):
            actual_image_path = self._convert_pdf_to_image(image_path)
        
        # 读取图像
        image = cv2.imread(actual_image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {actual_image_path}")
        
        # 使用 YOLOv8 表格检测模型
        if self.model is not None:
            try:
                logger.info("使用 YOLOv8 进行表格检测...")
                results = self.model(actual_image_path, conf=0.25)
                boxes = []
                
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = self.model.names.get(cls_id, 'unknown')
                        
                        logger.debug(f"检测到: {cls_name}, 置信度: {confidence:.2f}")
                        boxes.append([int(x1), int(y1), int(x2), int(y2), float(confidence)])
                
                if boxes:
                    logger.info(f"YOLOv8 检测到 {len(boxes)} 个表格")
                    return boxes
                else:
                    logger.info("YOLOv8 未检测到表格，使用备用方法")
                    
            except Exception as e:
                logger.error(f"YOLOv8 检测失败: {e}")
        
        return self._fallback_detection(image)
    
    def _fallback_detection(self, image):
        """备用检测方法：基于轮廓的表格检测"""
        logger.info("使用备用方法（轮廓检测）...")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = image.shape[:2]
        
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 检测水平线
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 40, 8), 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
        
        # 检测垂直线
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 40, 8)))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
        
        table_mask = cv2.add(horizontal, vertical)
        table_mask = cv2.dilate(table_mask, None, iterations=3)
        
        # 使用 RETR_EXTERNAL 获取外部轮廓
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        # 降低最小面积阈值，允许检测较小的表格
        min_area = (w * h) * 0.005  # 0.5% 的图片面积
        min_width = w * 0.08  # 最小宽度为图片宽度的 8%
        min_height = h * 0.03  # 最小高度为图片高度的 3%
        
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch
            # 放宽条件：面积足够大，或者宽高比例合理
            if area > min_area and cw > min_width and ch > min_height:
                # 稍微扩展边界框
                padding = 5
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(w, x + cw + padding)
                y2 = min(h, y + ch + padding)
                boxes.append([x1, y1, x2, y2, 0.5])
        
        # 按 y 坐标排序（从上到下）
        boxes.sort(key=lambda b: b[1])
        
        if not boxes:
            logger.info("备用方法未检测到明显表格，使用整张图片")
            boxes.append([0, 0, w, h, 0.3])
        else:
            logger.info(f"备用方法检测到 {len(boxes)} 个可能的表格区域")
        
        return boxes
    
    def crop_table(self, image_path, box):
        """裁剪表格区域"""
        actual_image_path = image_path
        if image_path.lower().endswith('.pdf'):
            actual_image_path = self._convert_pdf_to_image(image_path)
            
        image = cv2.imread(actual_image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {actual_image_path}")
            
        x1, y1, x2, y2 = box[:4]
        h, w = image.shape[:2]
        x1 = max(0, min(int(x1), w))
        y1 = max(0, min(int(y1), h))
        x2 = max(0, min(int(x2), w))
        y2 = max(0, min(int(y2), h))
        
        return image[y1:y2, x1:x2]
    
    def _convert_pdf_to_image(self, pdf_path, page_num=0):
        """将 PDF 指定页转换为图像"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                page_num = 0
            page = doc[page_num]
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            temp_path = pdf_path.rsplit('.', 1)[0] + f'_page{page_num}_converted.png'
            pix.save(temp_path)
            doc.close()
            logger.debug(f"PDF 转换完成: {temp_path}")
            return temp_path
        except ImportError:
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=200)
                if images:
                    temp_path = pdf_path.rsplit('.', 1)[0] + f'_page{page_num}_converted.png'
                    images[0].save(temp_path, 'PNG')
                    return temp_path
            except ImportError:
                pass
        raise ValueError("无法处理 PDF 文件，请安装 PyMuPDF: pip install pymupdf")
    
    def get_pdf_page_count(self, pdf_path):
        """获取 PDF 页数"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 1
    
    def detect_all_pages(self, image_path, max_pages=None):
        """
        检测所有页面中的表格（支持多页 PDF）
        
        Args:
            image_path: 图片或 PDF 路径
            max_pages: 最大处理页数（None 表示不限制）
        
        Returns:
            dict: {
                'pages': [{'page': page_num, 'boxes': [...], 'image_path': path}, ...],
                'total_pages': 总页数,
                'processed_pages': 实际处理页数,
                'slow_warning': 是否显示慢速警告
            }
        """
        results = []
        total_pages = 1
        slow_warning = False
        slow_threshold = int(os.environ.get('PDF_SLOW_THRESHOLD', 20))
        
        if image_path.lower().endswith('.pdf'):
            total_pages = self.get_pdf_page_count(image_path)
            process_pages = total_pages if max_pages is None else min(total_pages, max_pages)
            
            if total_pages > slow_threshold:
                slow_warning = True
                logger.warning(f"PDF 共 {total_pages} 页，处理可能较慢")
            
            logger.info(f"PDF 共 {total_pages} 页")
            
            for page_num in range(process_pages):
                logger.info(f"处理 PDF 第 {page_num + 1}/{process_pages} 页...")
                page_image_path = self._convert_pdf_to_image(image_path, page_num)
                boxes = self.detect(page_image_path)
                results.append({
                    'page': page_num,
                    'boxes': boxes,
                    'image_path': page_image_path
                })
        else:
            boxes = self.detect(image_path)
            results.append({
                'page': 0,
                'boxes': boxes,
                'image_path': image_path
            })
        
        return {
            'pages': results,
            'total_pages': total_pages,
            'processed_pages': len(results),
            'slow_warning': slow_warning
        }
