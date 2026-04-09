# 表格数据解析系统

一个基于深度学习的本地私有化表格数据解析应用，采用三步流水线架构：

**表格检测 (YOLOv8) → 结构解析 (PubTabNet) → 单元格 OCR (PaddleOCR)**

支持**多页 PDF 处理**，无页数限制。

## 主要功能

- **智能表格检测**: YOLOv8 自动定位图片中的表格区域，备用轮廓检测支持同页多表格
- **结构解析**: PPStructure v2 (PubTabNet) 模型识别表格行列结构
- **文字识别**: PaddleOCR 中英文混合识别
- **多页 PDF 支持**: 自动解析 PDF 所有页面，无页数限制（大文档会提示处理较慢）
- **检测预览**: 可视化显示检测到的表格区域
- **实时进度**: 显示解析进度和预计剩余时间
- **多格式导出**: 支持 CSV、Excel、JSON 格式导出
- **一键复制**: 快速复制表格数据到剪贴板

## 技术架构

| 步骤     | 技术                       | 说明                                                       |
| -------- | -------------------------- | ---------------------------------------------------------- |
| 表格检测 | YOLOv8                     | 使用专用表格检测模型 `keremberke/yolov8m-table-extraction` |
| 结构解析 | PPStructure v2 (PubTabNet) | 基于 PubTabNet 数据集训练的表格结构识别模型                |
| 文字识别 | PaddleOCR                  | 对每个单元格进行独立的中英文 OCR 识别                      |

> **PubTabNet**: IBM 发布的表格结构识别基准数据集，包含 568,000+ 张表格图像。
> PPStructure v2 使用该数据集训练，在测试集上 TEDS 准确率达 96.7%。

## 快速开始

### Docker Compose 部署（推荐）

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 访问地址

- **前端界面**: http://localhost:3000
- **后端 API**: http://localhost:5001
- **健康检查**: http://localhost:5001/api/health

## 离线部署 (本地私有化)

✅ **Docker 镜像在构建时预下载所有模型，支持完全离线运行**

### 预置模型

| 模型               | 来源        | 大小   | 说明                                  |
| ------------------ | ----------- | ------ | ------------------------------------- |
| YOLOv8 表格检测    | HuggingFace | ~50MB  | `keremberke/yolov8m-table-extraction` |
| PubTabNet 结构解析 | PaddleOCR   | ~100MB | PPStructure v2 表格结构识别模型       |
| PaddleOCR 文字识别 | PaddleOCR   | ~150MB | 中英文 OCR 模型                       |

### 部署流程

```bash
# 1. 构建镜像（需要网络，模型会被打包进镜像）
docker-compose build

# 2. 运行（无需网络，完全离线）
docker-compose up -d

# 3. 验证服务
curl http://localhost:5001/api/health
```

### 离线验证

```bash
# 构建完成后，可断开网络测试离线能力
docker-compose up -d
# 断开网络...
curl http://localhost:5001/api/health  # 应返回 {"status": "ok"}
```

### 数据安全

- 所有数据处理在本地完成，不依赖任何外部 API
- 上传的文件和解析结果仅存储在本地容器卷中
- 适合内网部署、离线环境、数据敏感场景

## 环境配置

支持通过环境变量或 `.env` 文件配置：

```bash
# 复制示例配置
cp backend/.env.example backend/.env
```

### 可配置项

| 变量                 | 默认值                                | 说明                                |
| -------------------- | ------------------------------------- | ----------------------------------- |
| `HOST`               | `0.0.0.0`                             | 服务监听地址                        |
| `PORT`               | `5000`                                | 服务端口                            |
| `DEBUG`              | `true`                                | 调试模式 (仅本地开发)               |
| `LOG_LEVEL`          | `INFO`                                | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `LOG_TO_FILE`        | `false`                               | 是否输出日志到文件                  |
| `LOG_DIR`            | `logs`                                | 日志文件目录                        |
| `MAX_CONTENT_LENGTH` | `16777216`                            | 最大上传文件大小 (16MB)             |
| `YOLO_MODEL`         | `keremberke/yolov8m-table-extraction` | YOLOv8 模型                         |
| `OCR_LANG`           | `ch`                                  | OCR 语言                            |
| `GUNICORN_WORKERS`   | `1`                                   | Gunicorn 工作进程数（建议保持 1）   |
| `GUNICORN_THREADS`   | `4`                                   | Gunicorn 线程数                     |
| `PDF_SLOW_THRESHOLD` | `20`                                  | PDF 页数超过此值时显示慢速警告      |

### 性能说明

- 使用 **gthread** 工作模式，支持多线程并发请求
- 模型推理使用线程锁保护，确保线程安全
- 大文档（超过 20 页）会显示处理较慢的提示

性能参考：

- 单页 PDF：约 3-5 秒
- 10 页 PDF：约 30-50 秒
- 20 页 PDF：约 60-100 秒

## 本地开发

### 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python app.py
```

### 前端

```bash
cd frontend-user
npm install
npm run dev
```

## 项目结构

```
.
├── backend/                    # 后端服务
│   ├── app.py                 # Flask 应用入口
│   ├── config.py              # 配置管理
│   ├── gunicorn.conf.py       # Gunicorn 生产服务器配置
│   ├── utils/
│   │   └── logger.py          # 日志模块
│   ├── modules/               # 核心模块
│   │   ├── table_detector.py  # YOLOv8 表格检测
│   │   ├── structure_parser.py # SLANet 结构解析
│   │   ├── ocr_engine.py      # PaddleOCR 文字识别
│   │   └── table_extractor.py # 流水线整合
│   ├── scripts/
│   │   └── download_models.py # 模型预下载脚本
│   ├── .env.example           # 环境变量示例
│   ├── requirements.txt
│   └── Dockerfile
├── frontend-user/             # 前端界面
│   ├── src/
│   │   ├── components/
│   │   │   └── TableParser.jsx
│   │   └── api/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── TECH_SPEC.md               # 技术规格说明
└── README.md
```

## API 接口

### 上传文件

```
POST /api/upload
Content-Type: multipart/form-data
Body: file (图片或 PDF)
```

### 解析表格

```
POST /api/parse
Content-Type: application/json
Body: { "filename": "上传的文件名" }
```

### 健康检查

```
GET /api/health
```

### 数据导出

```
POST /api/export/csv
Content-Type: application/json
Body: { "tables": [...], "table_index": 0 }
Response: CSV 文件下载
```

```
POST /api/export/excel
Content-Type: application/json
Body: { "tables": [...], "table_index": 0, "export_all": false }
Response: Excel 文件下载 (.xlsx)
```

```
POST /api/export/json
Content-Type: application/json
Body: { "tables": [...], "table_index": 0, "export_all": false }
Response: JSON 文件下载
```

### 检测预览

```
GET /api/preview/<filename>     # 获取上传图片预览
POST /api/detect-preview        # 获取带检测框的预览图
Body: { "filename": "..." }
```

### 历史记录（已移除）

历史记录功能已移除，解析结果仅在当前会话中显示。

### 批量处理

```
POST /api/batch/upload          # 批量上传文件 (multipart/form-data)
POST /api/batch/parse           # 批量解析表格
Body: { "filenames": ["file1.png", "file2.pdf"] }
```

## 支持格式

### 输入格式

- 图片: PNG, JPG, JPEG, TIFF, BMP
- 文档: PDF
- 文件大小限制: 16MB

### 导出格式

- CSV: 单个表格导出为逗号分隔值文件
- Excel: 支持单表格或全部表格导出 (.xlsx)，带格式化样式
- JSON: 结构化数据导出，包含元数据

## 技术栈

### 后端

- Python 3.11
- Flask 3.x + Flask-CORS
- **Gunicorn** - 生产级 WSGI 服务器
- PyTorch + Ultralytics (YOLOv8) - 表格检测
- PaddlePaddle + PaddleOCR 2.9.x + PPStructure (SLANet) - 结构解析与文字识别
- OpenCV + Pillow - 图像处理
- PyMuPDF - PDF 处理
- python-dotenv - 配置管理

### 前端

- React 18.2 + Vite 5
- Ant Design 5.12
- Axios 1.6

## 运行测试

```bash
# 后端测试
cd backend
pip install -r requirements-test.txt
pytest tests/ -v

# 前端测试
cd frontend-user
npm run test
```

## 注意事项

1. **生产服务器**: 使用 Gunicorn WSGI 服务器，支持多进程并发
2. **离线部署**: 构建时预下载所有模型，运行时无需网络
3. **内存要求**: 建议至少 4GB 可用内存
4. **架构支持**: 支持 amd64 和 arm64 架构（Docker 多架构构建）
5. **备用方案**: 如果专用模型加载失败，系统会自动使用 OpenCV 备用检测方案
6. **健康检查**: Docker 容器配置了健康检查，启动后 60 秒开始检测
7. **请求超时**: Gunicorn 配置 300 秒超时，适合大文件解析

## 故障排除

### 构建失败 (模型下载)

```bash
# 构建时需要网络下载模型，检查网络连接
docker-compose build --no-cache

# 查看构建日志
docker-compose build 2>&1 | tee build.log
```

### 内存不足

```bash
# 检查容器内存使用
docker stats table-parser-backend

# 减少 Gunicorn 工作进程数
# 在 docker-compose.yml 中添加环境变量:
# GUNICORN_WORKERS=1
```

### 端口冲突

```bash
# 修改 docker-compose.yml 中的端口映射
# 例如将 "3000:80" 改为 "8080:80"
```

### 请求超时

```bash
# 大文件解析可能需要更长时间
# 当前配置: Gunicorn 超时 300 秒
# 如需调整，修改 backend/gunicorn.conf.py 中的 timeout 值
```

## License

MIT
