# 后端服务文档

## 项目简介

表格数据解析系统的后端服务，基于Flask框架，提供表格检测、结构解析和OCR识别的RESTful API。

## 技术栈

- **框架**: Flask 3.0
- **表格检测**: YOLOv8 (Ultralytics) - `keremberke/yolov8m-table-extraction`
- **结构解析**: SLANet (基于 PubTabNet 数据集训练) - PaddleOCR PPStructure
- **OCR引擎**: PaddleOCR 2.9.x (中英文)
- **Python版本**: 3.9+

> **关于 TableNet vs SLANet**: SLANet 是 PubTabNet 数据集上的 SOTA 实现，
> 相比早期 TableNet 架构准确率提升 7%+。详见项目根目录 `TECH_SPEC.md`

## 快速开始

### 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 运行服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

### Docker运行

```bash
docker build -t table-parser-backend .
docker run -p 5000:5000 table-parser-backend
```

## API接口

### 健康检查

```
GET /api/health
```

响应：

```json
{
  "status": "ok",
  "message": "表格解析服务运行正常"
}
```

### 上传文件

```
POST /api/upload
Content-Type: multipart/form-data
Body: file (图片文件)
```

响应：

```json
{
  "success": true,
  "filename": "20240101_120000_test.png",
  "filepath": "/app/uploads/20240101_120000_test.png"
}
```

### 解析表格

```
POST /api/parse
Content-Type: application/json
Body: {
    "filename": "上传的文件名"
}
```

响应：

```json
{
  "success": true,
  "result": {
    "tables": [...],
    "total_tables": 1
  },
  "result_file": "result_xxx.json"
}
```

### 获取结果

```
GET /api/results/<filename>
```

## 项目结构

```
backend/
├── app.py                 # Flask应用主文件
├── modules/               # 核心模块
│   ├── table_detector.py    # 表格检测模块
│   ├── structure_parser.py  # 结构解析模块
│   ├── ocr_engine.py        # OCR引擎模块
│   └── table_extractor.py   # 表格提取器
├── tests/                   # 测试用例
├── requirements.txt        # Python依赖
└── Dockerfile             # Docker配置
```

## 配置说明

### 环境变量

- `FLASK_ENV`: 运行环境（development/production）
- `FLASK_APP`: 应用入口文件（默认app.py）

### 文件配置

在 `app.py` 中可以修改：

- 端口号：默认 5000
- 文件大小限制：默认 16MB
- 支持的文件格式：`ALLOWED_EXTENSIONS`

## 测试

```bash
pip install -r requirements-test.txt
pytest tests/ -v
```

## 开发

### 代码规范

- 遵循PEP 8编码规范
- 使用类型提示（Type Hints）
- 编写单元测试

### 模型配置

- **表格检测模型**：`modules/table_detector.py` 中的 `model_path`
- **结构解析模型**：`modules/structure_parser.py` 中的模型类型
- **OCR语言**：`modules/ocr_engine.py` 中的 `lang` 参数

## 部署

### Docker部署

```bash
docker build -t table-parser-backend .
docker run -d -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/results:/app/results \
  table-parser-backend
```

### 生产环境建议

1. 使用Gunicorn作为WSGI服务器
2. 配置Nginx作为反向代理
3. 使用环境变量管理配置
4. 启用日志记录和监控

## 许可证

MIT License
