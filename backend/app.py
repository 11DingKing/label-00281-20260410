"""
表格数据解析应用 - Flask 后端服务

采用 Application Factory 模式，支持：
- 依赖注入（便于测试）
- 服务层架构（关注点分离）
- 单例模型管理（避免重复加载）
"""
import os
import json
import base64
import logging

import cv2
import numpy as np
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime

from config import config
from utils.logger import setup_logger
from services.model_service import ModelService
from services.history_service import HistoryService
from services.export_service import ExportService, ExportError

# 初始化日志
logger = setup_logger('app')


def create_app(test_config=None) -> Flask:
    """
    Application Factory - 创建 Flask 应用实例
    
    Args:
        test_config: 测试配置（可选）
        
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if test_config:
        app.config.update(test_config)
    else:
        app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
        app.config['RESULTS_FOLDER'] = config.RESULTS_FOLDER
        app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    
    # 确保目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('RESULTS_FOLDER', 'results'), exist_ok=True)
    
    # 历史记录目录
    history_folder = os.path.join(
        os.path.dirname(app.config.get('UPLOAD_FOLDER', 'uploads')), 
        'history'
    )
    os.makedirs(history_folder, exist_ok=True)
    
    # 配置 CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": config.CORS_ORIGINS + ["http://frontend-user:80"],
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # 初始化服务（依赖注入）
    model_service = ModelService.get_instance()
    history_service = HistoryService(
        history_folder=history_folder,
        results_folder=app.config.get('RESULTS_FOLDER', 'results')
    )
    export_service = ExportService()
    
    # 将服务绑定到 app（便于在路由中访问）
    app.model_service = model_service
    app.history_service = history_service
    app.export_service = export_service
    
    # 注册路由
    _register_routes(app)
    
    return app


def _register_routes(app: Flask) -> None:
    """注册所有路由"""
    
    # ==================== 辅助函数 ====================
    
    def allowed_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS
    
    # ==================== 健康检查 ====================
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """健康检查"""
        return jsonify({
            'status': 'ok',
            'message': '表格解析服务运行正常',
            'models_loaded': app.model_service.is_initialized
        })
    
    # ==================== 文件上传 ====================
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """上传图片文件"""
        if 'file' not in request.files:
            logger.warning("上传请求缺少文件")
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("上传文件名为空")
            return jsonify({'error': '文件名为空'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            logger.info(f"文件上传成功: {filename}")
            
            # 如果是 PDF，获取页数信息
            pdf_info = None
            if filename.lower().endswith('.pdf'):
                try:
                    import fitz
                    doc = fitz.open(filepath)
                    total_pages = len(doc)
                    doc.close()
                    
                    slow_threshold = int(os.environ.get('PDF_SLOW_THRESHOLD', 20))
                    pdf_info = {
                        'total_pages': total_pages,
                        'slow_warning': total_pages > slow_threshold
                    }
                    
                    if total_pages > slow_threshold:
                        logger.info(f"PDF 共 {total_pages} 页，处理可能较慢")
                except Exception as e:
                    logger.error(f"获取 PDF 页数失败: {e}")
            
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'pdf_info': pdf_info
            })
        
        logger.warning(f"不支持的文件类型: {file.filename}")
        return jsonify({'error': '不支持的文件类型'}), 400
    
    # ==================== 表格解析 ====================
    
    @app.route('/api/parse', methods=['POST'])
    def parse_table():
        """解析表格"""
        try:
            data = request.json
            filename = data.get('filename')
            
            if not filename:
                logger.warning("解析请求缺少文件名")
                return jsonify({'error': '缺少文件名'}), 400
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(filepath):
                logger.warning(f"文件不存在: {filepath}")
                return jsonify({'error': '文件不存在'}), 404
            
            logger.info(f"开始解析文件: {filename}")
            
            # 使用模型服务进行解析
            result = app.model_service.table_extractor.extract(filepath)
            
            # 保存结果
            result_filename = f"result_{filename.rsplit('.', 1)[0]}.json"
            result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # 添加到历史记录
            history_record = app.history_service.add({
                'filename': filename,
                'original_name': filename.split('_', 2)[-1] if '_' in filename else filename,
                'result_file': result_filename,
                'total_tables': result.get('total_tables', 0),
                'total_pages': result.get('total_pages', 1)
            })
            
            logger.info(f"解析完成，结果保存至: {result_filename}")
            
            return jsonify({
                'success': True,
                'result': result,
                'result_file': result_filename,
                'history_id': history_record.get('id')
            })
        
        except Exception as e:
            logger.error(f"解析失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'解析失败: {str(e)}'}), 500
    
    @app.route('/api/results/<filename>', methods=['GET'])
    def get_result(filename):
        """获取解析结果"""
        result_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return jsonify(result)
        return jsonify({'error': '结果文件不存在'}), 404
    
    # ==================== 导出功能 ====================
    
    @app.route('/api/export/csv', methods=['POST'])
    def export_csv():
        """导出表格数据为 CSV 格式"""
        try:
            data = request.json
            tables = data.get('tables', [])
            table_index = data.get('table_index', 0)
            
            csv_content, filename = ExportService.export_csv(tables, table_index)
            
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )
        except ExportError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"CSV 导出失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'导出失败: {str(e)}'}), 500
    
    @app.route('/api/export/excel', methods=['POST'])
    def export_excel():
        """导出表格数据为 Excel 格式"""
        try:
            data = request.json
            tables = data.get('tables', [])
            table_index = data.get('table_index', 0)
            export_all = data.get('export_all', False)
            
            excel_content, filename = ExportService.export_excel(
                tables, table_index, export_all
            )
            
            return Response(
                excel_content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            )
        except ExportError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Excel 导出失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'导出失败: {str(e)}'}), 500
    
    @app.route('/api/export/json', methods=['POST'])
    def export_json():
        """导出表格数据为 JSON 格式"""
        try:
            data = request.json
            tables = data.get('tables', [])
            table_index = data.get('table_index', 0)
            export_all = data.get('export_all', False)
            
            json_content, filename = ExportService.export_json(
                tables, table_index, export_all
            )
            
            return Response(
                json_content,
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': 'application/json; charset=utf-8'
                }
            )
        except ExportError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"JSON 导出失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'导出失败: {str(e)}'}), 500
    
    # ==================== 预览功能 ====================
    
    @app.route('/api/preview/<filename>', methods=['GET'])
    def preview_image(filename):
        """获取上传图片的预览"""
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        if filename.lower().endswith('.pdf'):
            try:
                import fitz
                doc = fitz.open(filepath)
                page = doc[0]
                zoom = 1.5
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                doc.close()
                return Response(img_data, mimetype='image/png')
            except Exception as e:
                logger.error(f"PDF 预览失败: {e}")
                return jsonify({'error': 'PDF 预览失败'}), 500
        
        return send_file(filepath)
    
    @app.route('/api/detect-preview', methods=['POST'])
    def detect_preview():
        """检测表格并返回带标注的预览图"""
        try:
            data = request.json
            filename = data.get('filename')
            
            if not filename:
                return jsonify({'error': '缺少文件名'}), 400
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(filepath):
                return jsonify({'error': '文件不存在'}), 404
            
            # 使用模型服务进行检测
            detect_result = app.model_service.table_detector.detect_all_pages(filepath)
            page_results = detect_result.get('pages', [])
            
            previews = []
            for page_data in page_results:
                page_num = page_data['page']
                boxes = page_data['boxes']
                image_path = page_data.get('image_path', filepath)
                
                image = cv2.imread(image_path)
                if image is None:
                    continue
                
                for idx, box in enumerate(boxes):
                    x1, y1, x2, y2 = [int(v) for v in box[:4]]
                    confidence = box[4] if len(box) > 4 else 0.5
                    
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    
                    label = f'Table {idx + 1} ({confidence:.0%})'
                    (label_w, label_h), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
                    )
                    cv2.rectangle(
                        image, (x1, y1 - label_h - 10), 
                        (x1 + label_w + 10, y1), (0, 255, 0), -1
                    )
                    cv2.putText(
                        image, label, (x1 + 5, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
                    )
                
                _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                previews.append({
                    'page': page_num,
                    'image': f'data:image/jpeg;base64,{img_base64}',
                    'tables_count': len(boxes),
                    'boxes': boxes
                })
            
            return jsonify({
                'success': True,
                'total_pages': len(previews),
                'previews': previews
            })
        
        except Exception as e:
            logger.error(f"检测预览失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'检测预览失败: {str(e)}'}), 500
    
    # ==================== 历史记录 ====================
    
    @app.route('/api/history', methods=['GET'])
    def get_history():
        """获取历史记录列表"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = app.history_service.list(page, per_page)
        return jsonify({'success': True, **result})
    
    @app.route('/api/history/<record_id>', methods=['GET'])
    def get_history_detail(record_id):
        """获取历史记录详情"""
        record = app.history_service.get_with_result(record_id)
        if record:
            return jsonify({'success': True, 'record': record})
        return jsonify({'error': '记录不存在'}), 404
    
    @app.route('/api/history/<record_id>', methods=['DELETE'])
    def delete_history(record_id):
        """删除历史记录"""
        if app.history_service.delete(record_id):
            return jsonify({'success': True, 'message': '删除成功'})
        return jsonify({'error': '记录不存在'}), 404
    
    @app.route('/api/history/clear', methods=['POST'])
    def clear_history():
        """清空历史记录"""
        count = app.history_service.clear()
        return jsonify({'success': True, 'message': f'已清空 {count} 条历史记录'})
    
    # ==================== 批量处理 ====================
    
    @app.route('/api/batch/upload', methods=['POST'])
    def batch_upload():
        """批量上传文件"""
        if 'files' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': '没有上传文件'}), 400
        
        uploaded = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                uploaded.append({
                    'original_name': file.filename,
                    'filename': filename,
                    'filepath': filepath
                })
            else:
                errors.append({
                    'filename': file.filename,
                    'error': '不支持的文件类型'
                })
        
        logger.info(f"批量上传完成: {len(uploaded)} 成功, {len(errors)} 失败")
        
        return jsonify({
            'success': True,
            'uploaded': uploaded,
            'errors': errors,
            'total_uploaded': len(uploaded),
            'total_errors': len(errors)
        })
    
    @app.route('/api/batch/parse', methods=['POST'])
    def batch_parse():
        """批量解析表格"""
        try:
            data = request.json
            filenames = data.get('filenames', [])
            
            if not filenames:
                return jsonify({'error': '缺少文件列表'}), 400
            
            results = []
            errors = []
            
            for idx, filename in enumerate(filenames):
                try:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if not os.path.exists(filepath):
                        errors.append({'filename': filename, 'error': '文件不存在'})
                        continue
                    
                    logger.info(f"批量解析 [{idx + 1}/{len(filenames)}]: {filename}")
                    
                    result = app.model_service.table_extractor.extract(filepath)
                    
                    result_filename = f"result_{filename.rsplit('.', 1)[0]}.json"
                    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
                    with open(result_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    history_record = app.history_service.add({
                        'filename': filename,
                        'original_name': filename.split('_', 2)[-1] if '_' in filename else filename,
                        'result_file': result_filename,
                        'total_tables': result.get('total_tables', 0),
                        'total_pages': result.get('total_pages', 1)
                    })
                    
                    results.append({
                        'filename': filename,
                        'result_file': result_filename,
                        'total_tables': result.get('total_tables', 0),
                        'total_pages': result.get('total_pages', 1),
                        'history_id': history_record.get('id')
                    })
                    
                except Exception as e:
                    logger.error(f"解析 {filename} 失败: {str(e)}")
                    errors.append({'filename': filename, 'error': str(e)})
            
            return jsonify({
                'success': True,
                'results': results,
                'errors': errors,
                'total_success': len(results),
                'total_errors': len(errors)
            })
        
        except Exception as e:
            logger.error(f"批量解析失败: {str(e)}", exc_info=True)
            return jsonify({'error': f'批量解析失败: {str(e)}'}), 500


# 创建应用实例（供 Gunicorn 使用）
app = create_app()


# Gunicorn 启动钩子
def on_starting(server):
    """Gunicorn 启动时预加载模型"""
    logger.info("=" * 50)
    logger.info("表格数据解析服务启动中...")
    logger.info("预加载 AI 模型...")
    logger.info("=" * 50)
    
    # 预加载模型（在 master 进程中）
    ModelService.get_instance().initialize()


# 开发模式直接运行
if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("启动表格数据解析后端服务 (开发模式)...")
    logger.info(f"后端API地址: http://{config.HOST}:{config.PORT}")
    
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV'):
        logger.info("前端地址: http://localhost:3000 (Docker Compose)")
    else:
        logger.info("前端地址: http://localhost:3000 (需单独启动)")
    
    logger.info("=" * 50)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
