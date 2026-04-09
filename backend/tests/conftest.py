"""
Pytest配置文件
"""
import pytest
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        'UPLOAD_FOLDER': 'test_uploads',
        'RESULTS_FOLDER': 'test_results',
    }
