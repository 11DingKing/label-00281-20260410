"""
表格提取器 - 整合三步串行流水线

处理流程 (严格串行):
1. 表格检测 (YOLOv8) - 定位图像中的表格区域
2. 结构解析 (SLANet/PubTabNet) - 识别表格的行列结构和单元格位置
3. 单元格 OCR (PaddleOCR) - 对每个单元格进行独立的文字识别
"""
import cv2
import numpy as np
import os
import logging

logger = logging.getLogger('table_parser.extractor')


class TableExtractor:
    def __init__(self, table_detector, structure_parser, ocr_engine):
        """
        初始化表格提取器
        
        Args:
            table_detector: YOLOv8 表格检测器
            structure_parser: SLANet 结构解析器
            ocr_engine: PaddleOCR 文字识别引擎
        """
        self.table_detector = table_detector
        self.structure_parser = structure_parser
        self.ocr_engine = ocr_engine
    
    def extract(self, image_path):
        """
        完整提取表格数据 (三步串行流水线)
        支持多页 PDF
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 步骤1: 表格检测 (YOLOv8) - 支持多页
        logger.info("=" * 50)
        logger.info("步骤1: 表格检测 (YOLOv8)")
        logger.info("=" * 50)
        
        # 使用 detect_all_pages 处理多页 PDF
        detect_result = self.table_detector.detect_all_pages(image_path)
        page_results = detect_result.get('pages', [])
        total_pages = detect_result.get('total_pages', 1)
        slow_warning = detect_result.get('slow_warning', False)
        
        if slow_warning:
            logger.warning(f"PDF 页数较多 ({total_pages} 页)，处理可能需要较长时间")
        
        if not page_results:
            logger.warning("未检测到任何页面")
            return {
                'tables': [],
                'message': '未检测到表格',
                'total_tables': 0,
                'total_pages': total_pages
            }
        
        total_table_count = sum(len(p.get('boxes', [])) for p in page_results)
        logger.info(f"共 {len(page_results)} 页，检测到 {total_table_count} 个表格区域")
        
        all_tables = []
        global_table_index = 0
        
        for page_data in page_results:
            page_num = page_data['page']
            table_boxes = page_data.get('boxes', [])
            page_image_path = page_data.get('image_path', image_path)
            
            if not table_boxes:
                logger.info(f"第 {page_num + 1} 页: 未检测到表格")
                continue
            
            logger.info(f"第 {page_num + 1} 页: {len(table_boxes)} 个表格")
            
            for idx, box in enumerate(table_boxes):
                logger.info(f"  处理表格 {idx + 1}/{len(table_boxes)}...")
                
                table_image = self.table_detector.crop_table(page_image_path, box)
                
                # 步骤2: 结构解析 (SLANet/PubTabNet)
                logger.info(f"  步骤2: 结构解析 (SLANet/PubTabNet)")
                
                structure = self.structure_parser.parse(table_image)
                logger.info(f"  识别到结构: {structure['rows']} 行 × {structure['cols']} 列")
                
                # 步骤3: 单元格 OCR (PaddleOCR)
                logger.info(f"  步骤3: 单元格 OCR (PaddleOCR)")
                
                table_data = self._ocr_table_cells(table_image, structure)
                
                all_tables.append({
                    'page': page_num,
                    'page_table_index': idx,
                    'global_index': global_table_index,
                    'bbox': box[:4],
                    'confidence': box[4] if len(box) > 4 else 0.5,
                    'structure': {
                        'rows': structure['rows'],
                        'cols': structure['cols']
                    },
                    'data': table_data
                })
                global_table_index += 1
        
        logger.info("=" * 50)
        logger.info(f"表格提取完成: 共 {len(all_tables)} 个表格")
        logger.info("=" * 50)
        
        return {
            'tables': all_tables,
            'total_tables': len(all_tables),
            'total_pages': total_pages,
            'processed_pages': len(page_results),
            'slow_warning': detect_result.get('slow_warning', False)
        }
    
    def _ocr_table_cells(self, table_image, structure):
        """对表格进行 OCR 识别"""
        cell_boxes = structure.get('cell_boxes', [])
        
        if cell_boxes and len(cell_boxes) > 0:
            logger.info(f"使用单元格级别 OCR ({len(cell_boxes)} 个单元格)")
            result = self._ocr_by_cells(table_image, structure)
            
            # 检查是否有有效结果
            has_content = any(any(cell for cell in row) for row in result)
            if has_content:
                return result
            
            logger.info("单元格 OCR 无结果，尝试整体 OCR...")
        
        logger.info("使用整体 OCR + 位置重建")
        return self._ocr_and_reconstruct(table_image, structure)
    
    def _ocr_by_cells(self, table_image, structure):
        """逐单元格进行 OCR"""
        rows = structure['rows']
        cols = structure['cols']
        cell_boxes = structure.get('cell_boxes', [])
        
        table_data = [['' for _ in range(cols)] for _ in range(rows)]
        sorted_cells = self._sort_cells_by_position(cell_boxes, rows, cols)
        
        ocr_count = 0
        for row_idx, row_cells in enumerate(sorted_cells):
            for col_idx, bbox in enumerate(row_cells):
                if bbox is None:
                    continue
                
                x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
                h, w = table_image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x2 > x1 + 5 and y2 > y1 + 5:
                    cell_image = table_image[y1:y2, x1:x2]
                    text = self.ocr_engine.recognize(cell_image)
                    
                    if row_idx < rows and col_idx < cols:
                        table_data[row_idx][col_idx] = text.strip() if text else ''
                        if text and text.strip():
                            ocr_count += 1
        
        logger.info(f"OCR 完成: 识别到 {ocr_count} 个非空单元格")
        return table_data
    
    def _sort_cells_by_position(self, cell_boxes, rows, cols):
        """将单元格按位置排序到行列网格中"""
        if not cell_boxes:
            return [[None] * cols for _ in range(rows)]
        
        y_coords = sorted(set([box[1] for box in cell_boxes if len(box) >= 4]))
        row_boundaries = self._cluster_boundaries(y_coords, rows)
        
        x_coords = sorted(set([box[0] for box in cell_boxes if len(box) >= 4]))
        col_boundaries = self._cluster_boundaries(x_coords, cols)
        
        grid = [[None] * cols for _ in range(rows)]
        
        for bbox in cell_boxes:
            if len(bbox) < 4:
                continue
            
            x, y = bbox[0], bbox[1]
            
            row_idx = 0
            for i, boundary in enumerate(row_boundaries[:-1]):
                if y >= boundary:
                    row_idx = i
            
            col_idx = 0
            for i, boundary in enumerate(col_boundaries[:-1]):
                if x >= boundary:
                    col_idx = i
            
            if row_idx < rows and col_idx < cols:
                grid[row_idx][col_idx] = bbox
        
        return grid
    
    def _cluster_boundaries(self, coords, num_clusters):
        """将坐标聚类成边界"""
        if not coords or num_clusters <= 1:
            return [0, float('inf')]
        
        min_coord = min(coords)
        max_coord = max(coords)
        step = (max_coord - min_coord) / num_clusters
        
        return [min_coord + i * step for i in range(num_clusters + 1)]
    
    def _ocr_and_reconstruct(self, table_image, structure):
        """整体 OCR 后按位置重建表格结构"""
        ocr_results = self.ocr_engine.recognize_with_positions(table_image)
        
        if not ocr_results:
            rows = structure.get('rows', 1)
            cols = structure.get('cols', 1)
            return [['' for _ in range(cols)] for _ in range(rows)]
        
        logger.info(f"OCR 识别到 {len(ocr_results)} 个文字区域")
        
        heights = [r['y_max'] - r['y_min'] for r in ocr_results]
        avg_height = np.mean(heights) if heights else 20
        row_threshold = avg_height * 0.8
        
        rows_data = self._cluster_into_rows(ocr_results, row_threshold)
        
        table_data = []
        for row in rows_data:
            sorted_row = sorted(row, key=lambda x: x['x_min'])
            row_texts = [item['text'] for item in sorted_row]
            table_data.append(row_texts)
        
        if table_data:
            max_cols = max(len(row) for row in table_data)
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
        
        return table_data
    
    def _cluster_into_rows(self, ocr_results, threshold):
        """根据 y 坐标将文字聚类成行"""
        if not ocr_results:
            return []
        
        sorted_results = sorted(ocr_results, key=lambda x: x['y'])
        
        rows = []
        current_row = [sorted_results[0]]
        current_y = sorted_results[0]['y']
        
        for item in sorted_results[1:]:
            if abs(item['y'] - current_y) < threshold:
                current_row.append(item)
            else:
                rows.append(current_row)
                current_row = [item]
                current_y = item['y']
        
        if current_row:
            rows.append(current_row)
        
        return rows
