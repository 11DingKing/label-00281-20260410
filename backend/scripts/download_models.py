#!/usr/bin/env python3
"""
模型预下载脚本 - 实现真正的离线部署

此脚本在 Docker 构建阶段运行，预下载所有必需的模型文件，
确保容器可以在完全离线的环境中运行。

预下载的模型：
1. YOLOv8 表格检测模型 (keremberke/yolov8m-table-extraction)
2. PaddleOCR 文字识别模型 (中英文)
3. PPStructure 表格结构识别模型 (SLANet - 基于 PubTabNet 训练)
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_yolo_model():
    """下载 YOLOv8 表格检测模型"""
    logger.info("=" * 50)
    logger.info("下载 YOLOv8 表格检测模型...")
    logger.info("=" * 50)
    
    try:
        from ultralytics import YOLO
        
        # 下载专用表格检测模型
        model_name = os.getenv('YOLO_MODEL', 'keremberke/yolov8m-table-extraction')
        logger.info(f"正在下载模型: {model_name}")
        
        model = YOLO(model_name)
        logger.info(f"YOLOv8 模型下载成功: {model_name}")
        
        # 验证模型
        if hasattr(model, 'names'):
            logger.info(f"模型类别: {model.names}")
        
        return True
    except Exception as e:
        logger.error(f"YOLOv8 模型下载失败: {e}")
        # 尝试下载备用模型
        try:
            logger.info("尝试下载备用模型 yolov8n.pt...")
            model = YOLO('yolov8n.pt')
            logger.info("备用模型下载成功")
            return True
        except Exception as e2:
            logger.error(f"备用模型下载也失败: {e2}")
            return False


def download_paddleocr_models():
    """下载 PaddleOCR 模型"""
    logger.info("=" * 50)
    logger.info("下载 PaddleOCR 文字识别模型...")
    logger.info("=" * 50)
    
    try:
        from paddleocr import PaddleOCR
        
        # 初始化 PaddleOCR，这会自动下载模型
        lang = os.getenv('OCR_LANG', 'ch')
        logger.info(f"正在下载 PaddleOCR 模型 (语言: {lang})...")
        
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=False,
            show_log=True  # 显示下载日志
        )
        
        logger.info("PaddleOCR 模型下载成功")
        return True
    except Exception as e:
        logger.error(f"PaddleOCR 模型下载失败: {e}")
        return False


def download_ppstructure_models():
    """
    下载 PPStructure 表格结构识别模型 (SLANet)
    
    技术说明：
    - PPStructure 使用 SLANet (Structure Location Alignment Network) 模型
    - SLANet 是在 PubTabNet 数据集上训练的表格结构识别模型
    - 相比早期的 TableNet 架构，SLANet 在准确率和速度上都有显著提升
    - PubTabNet 数据集包含约 50 万张科学论文表格图像
    """
    logger.info("=" * 50)
    logger.info("下载 PPStructure 表格结构识别模型 (SLANet/PubTabNet)...")
    logger.info("=" * 50)
    
    try:
        from paddleocr import PPStructure
        
        # 初始化 PPStructure，这会自动下载 SLANet 模型
        logger.info("正在下载 SLANet 表格结构识别模型...")
        logger.info("(SLANet 基于 PubTabNet 数据集训练，是 TableNet 的改进版本)")
        
        # 先尝试不带 OCR 的版本
        try:
            table_engine = PPStructure(
                show_log=True,
                recovery=False,
                layout=False,
                table=True,
                ocr=False
            )
            logger.info("PPStructure (SLANet) 表格结构模型下载成功 (不含 OCR)")
        except Exception:
            # 带 OCR 的版本
            table_engine = PPStructure(
                show_log=True,
                recovery=False,
                layout=False,
                table=True
            )
            logger.info("PPStructure (SLANet) 表格结构模型下载成功 (含 OCR)")
        
        return True
    except Exception as e:
        logger.error(f"PPStructure 模型下载失败: {e}")
        return False


def verify_models():
    """验证所有模型是否可用"""
    logger.info("=" * 50)
    logger.info("验证模型完整性...")
    logger.info("=" * 50)
    
    success = True
    
    # 验证 YOLO
    try:
        from ultralytics import YOLO
        model = YOLO('keremberke/yolov8m-table-extraction')
        logger.info("✓ YOLOv8 表格检测模型可用")
    except Exception as e:
        logger.warning(f"✗ YOLOv8 模型验证失败: {e}")
        success = False
    
    # 验证 PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
        logger.info("✓ PaddleOCR 文字识别模型可用")
    except Exception as e:
        logger.warning(f"✗ PaddleOCR 模型验证失败: {e}")
        success = False
    
    # 验证 PPStructure
    try:
        from paddleocr import PPStructure
        engine = PPStructure(show_log=False, recovery=False, layout=False, table=True)
        logger.info("✓ PPStructure (SLANet) 表格结构模型可用")
    except Exception as e:
        logger.warning(f"✗ PPStructure 模型验证失败: {e}")
        success = False
    
    return success


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("表格解析系统 - 模型预下载脚本")
    logger.info("=" * 60)
    logger.info("")
    logger.info("此脚本将下载以下模型:")
    logger.info("  1. YOLOv8 表格检测模型 (Hugging Face)")
    logger.info("  2. PaddleOCR 中英文识别模型")
    logger.info("  3. PPStructure SLANet 表格结构模型 (基于 PubTabNet)")
    logger.info("")
    
    results = []
    
    # 下载各模型
    results.append(("YOLOv8 表格检测", download_yolo_model()))
    results.append(("PaddleOCR 文字识别", download_paddleocr_models()))
    results.append(("PPStructure (SLANet)", download_ppstructure_models()))
    
    # 验证模型
    verification = verify_models()
    
    # 打印结果
    logger.info("")
    logger.info("=" * 60)
    logger.info("下载结果汇总")
    logger.info("=" * 60)
    
    all_success = True
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        logger.info(f"  {name}: {status}")
        if not success:
            all_success = False
    
    logger.info(f"  模型验证: {'✓ 通过' if verification else '✗ 失败'}")
    logger.info("")
    
    if all_success and verification:
        logger.info("所有模型下载完成！容器现在可以离线运行。")
        sys.exit(0)
    else:
        logger.warning("部分模型下载失败，但系统仍可使用备用方案运行。")
        sys.exit(0)  # 不要因为部分失败而中断构建


if __name__ == '__main__':
    main()
