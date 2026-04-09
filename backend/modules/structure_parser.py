"""
表格结构解析模块 - 使用 SLANet 模型进行表格结构识别

技术说明:
- SLANet (Structure Location Alignment Network) 是基于 PubTabNet 数据集训练的表格结构识别模型
- PubTabNet 是表格结构识别领域的标准基准数据集，包含约 50 万张表格图像
- SLANet 采用了更先进的特征提取和对齐机制，相比早期的 TableNet 架构有显著改进
- 本模块仅负责表格结构解析（行列、单元格位置），不进行 OCR 文字识别
"""
import cv2
import numpy as np
import os
import re
import logging
import threading

logger = logging.getLogger('table_parser.structure')


class StructureParser:
    # 类级别的锁，保护模型推理（PaddleOCR 不是线程安全的）
    _inference_lock = threading.Lock()
    
    def __init__(self):
        """
        初始化结构解析器
        使用 SLANet 模型 (基于 PubTabNet 数据集训练)
        """
        self.table_engine = None
        
        try:
            logger.info("初始化 SLANet 表格结构识别模型 (PubTabNet)...")
            from paddleocr import PPStructure
            
            self.table_engine = PPStructure(
                show_log=False,
                recovery=False,
                layout=False,
                table=True,
                ocr=False
            )
            logger.info("SLANet 表格结构识别模型初始化成功")
            
        except Exception as e:
            logger.warning(f"SLANet 初始化失败 (ocr=False): {e}")
            try:
                from paddleocr import PPStructure
                self.table_engine = PPStructure(
                    show_log=False,
                    recovery=False,
                    layout=False,
                    table=True
                )
                logger.info("SLANet 表格结构识别模型初始化成功 (带内置OCR)")
            except Exception as e2:
                logger.error(f"PPStructure 初始化失败: {e2}")
                self.table_engine = None
    
    def parse(self, table_image):
        """
        解析表格结构 (仅结构，不含文字内容)
        
        Args:
            table_image: 表格图像（numpy数组或图像路径）
            
        Returns:
            dict: 包含表格结构信息
        """
        if isinstance(table_image, str):
            if not os.path.exists(table_image):
                raise FileNotFoundError(f"图像文件不存在: {table_image}")
            table_image = cv2.imread(table_image)
        
        if table_image is None:
            raise ValueError("无法读取表格图像")
        
        if self.table_engine is not None:
            try:
                # 使用锁保护模型推理
                with self._inference_lock:
                    return self._parse_with_slanet(table_image)
            except Exception as e:
                logger.error(f"SLANet 解析失败: {e}")
        
        return self._fallback_parse(table_image)
    
    def _parse_with_slanet(self, image):
        """使用 SLANet (PPStructure) 解析表格结构"""
        result = self.table_engine(image)
        
        if not result:
            return self._fallback_parse(image)
        
        table_result = None
        for item in result:
            if item.get('type') == 'table' or 'res' in item:
                table_result = item
                break
        
        if table_result is None:
            return self._fallback_parse(image)
        
        res = table_result.get('res', {})
        cell_boxes = res.get('cell_bbox', [])
        
        logger.debug(f"SLANet 返回 {len(cell_boxes)} 个单元格边界框")
        
        html = res.get('html', '')
        rows, cols = self._parse_html_dimensions(html)
        
        cells = []
        valid_cell_boxes = []
        for i, bbox in enumerate(cell_boxes):
            if isinstance(bbox, (list, tuple)):
                if len(bbox) == 4 and not isinstance(bbox[0], (list, tuple)):
                    x1, y1, x2, y2 = bbox
                elif len(bbox) >= 4 and isinstance(bbox[0], (list, tuple)):
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                else:
                    continue
                
                cells.append({'index': i, 'bbox': [int(x1), int(y1), int(x2), int(y2)]})
                valid_cell_boxes.append([int(x1), int(y1), int(x2), int(y2)])
        
        logger.info(f"结构解析完成: {rows}行 x {cols}列, {len(valid_cell_boxes)} 个单元格")
        
        return {
            'rows': rows,
            'cols': cols,
            'cells': cells,
            'cell_boxes': valid_cell_boxes,
            'html_structure': html
        }
    
    def _parse_html_dimensions(self, html):
        """从 HTML 解析表格行列数"""
        if not html:
            return 1, 1
        rows = len(re.findall(r'<tr[^>]*>', html, re.IGNORECASE))
        first_row = re.search(r'<tr[^>]*>(.*?)</tr>', html, re.IGNORECASE | re.DOTALL)
        cols = len(re.findall(r'<t[dh][^>]*>', first_row.group(1), re.IGNORECASE)) if first_row else 1
        return max(rows, 1), max(cols, 1)
    
    def _fallback_parse(self, image):
        """备用解析方法（基于图像处理）"""
        logger.info("使用备用方法进行结构解析...")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 30, 10), 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
        
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 30, 10)))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
        
        table_mask = cv2.add(horizontal, vertical)
        contours, _ = cv2.findContours(table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        cells = []
        cell_boxes = []
        min_area = (w * h) / 500
        
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            if cw * ch > min_area and cw > 10 and ch > 10:
                bbox = [x, y, x + cw, y + ch]
                cells.append({'index': len(cells), 'bbox': bbox})
                cell_boxes.append(bbox)
        
        if cells:
            y_coords = sorted(set([c['bbox'][1] for c in cells]))
            x_coords = sorted(set([c['bbox'][0] for c in cells]))
            rows = self._cluster_count(y_coords, h // 20)
            cols = self._cluster_count(x_coords, w // 20)
        else:
            rows, cols = 1, 1
        
        return {
            'rows': max(rows, 1),
            'cols': max(cols, 1),
            'cells': cells[:100],
            'cell_boxes': cell_boxes[:100],
            'html_structure': ''
        }
    
    def _cluster_count(self, coords, threshold):
        if not coords:
            return 1
        count = 1
        prev = coords[0]
        for coord in coords[1:]:
            if coord - prev > threshold:
                count += 1
            prev = coord
        return count
