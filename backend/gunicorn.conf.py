"""
Gunicorn 配置文件 - 生产环境 WSGI 服务器

关键配置说明：
1. workers=1: 深度学习模型内存占用大，单 Worker 避免 OOM
2. preload_app=True: 在 master 进程预加载模型，fork 后 Worker 共享内存（COW）
3. timeout=300: 大型 PDF 解析可能需要较长时间
"""
import os

# ==================== 绑定配置 ====================
bind = "0.0.0.0:5000"

# ==================== Worker 配置 ====================
# 默认单 Worker，避免深度学习模型重复加载导致 OOM
# 如需多 Worker，请确保机器内存充足（每个 Worker 约需 2-3GB）
workers = int(os.getenv("GUNICORN_WORKERS", 1))

# 使用 gthread 模式支持并发请求
# 这样解析任务不会阻塞历史记录等轻量级请求
worker_class = "gthread"

# 每个 Worker 的线程数（处理并发请求）
threads = int(os.getenv("GUNICORN_THREADS", 4))

# ==================== 超时配置 ====================
# 请求超时时间（大型 PDF 解析可能需要 5 分钟）
timeout = 300

# 优雅关闭超时
graceful_timeout = 30

# 保持连接时间
keepalive = 5

# ==================== 内存管理 ====================
# 单 Worker 模式下关闭自动重启（避免重新加载模型）
max_requests = 0 if workers == 1 else 500
max_requests_jitter = 0 if workers == 1 else 50

# ==================== 日志配置 ====================
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# ==================== 进程配置 ====================
proc_name = "table-parser"

# 预加载应用（关键：在 master 进程加载模型，Worker 共享内存）
preload_app = True


# ==================== 生命周期钩子 ====================

def on_starting(server):
    """
    Gunicorn master 进程启动时调用
    
    在这里预加载 AI 模型，确保：
    1. 模型只加载一次
    2. fork 后的 Worker 通过 Copy-on-Write 共享模型内存
    """
    print("=" * 60)
    print("表格数据解析服务启动中...")
    print("=" * 60)
    print(f"  - 工作进程数: {workers}")
    print(f"  - 每进程线程数: {threads}")
    print(f"  - 请求超时: {timeout}s")
    print(f"  - 预加载模式: {'启用' if preload_app else '禁用'}")
    print("=" * 60)
    
    # 预加载 AI 模型
    print("\n正在预加载 AI 模型（YOLOv8 + PubTabNet + PaddleOCR）...")
    try:
        from services.model_service import ModelService
        ModelService.get_instance().initialize()
        print("模型预加载完成！\n")
    except Exception as e:
        print(f"警告：模型预加载失败: {e}")
        print("模型将在首次请求时加载\n")


def post_fork(server, worker):
    """Worker 进程 fork 后调用"""
    print(f"Worker {worker.pid} 已启动")


def worker_exit(server, worker):
    """Worker 进程退出时调用"""
    print(f"Worker {worker.pid} 已退出")


def on_exit(server):
    """Gunicorn 完全退出时调用"""
    print("=" * 60)
    print("表格数据解析服务已停止")
    print("=" * 60)
