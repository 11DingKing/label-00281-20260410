"""
日志配置模块
提供统一的日志管理，支持分级控制和文件输出
"""
import logging
import os
from datetime import datetime


def setup_logger(name='table_parser', level=None):
    """
    配置并返回 logger 实例
    
    Args:
        name: logger 名称
        level: 日志级别，默认从环境变量读取
        
    Returns:
        logging.Logger 实例
    """
    # 从环境变量获取日志级别
    if level is None:
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_str, logging.INFO)
    
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出（可选）
    log_to_file = os.getenv('LOG_TO_FILE', 'false').lower() == 'true'
    if log_to_file:
        log_dir = os.getenv('LOG_DIR', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 默认 logger 实例
logger = setup_logger()
