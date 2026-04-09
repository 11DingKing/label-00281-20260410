"""
后端API测试用例
"""
import pytest
import os
import json
import tempfile
from io import BytesIO
from PIL import Image
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    app.config['RESULTS_FOLDER'] = tempfile.mkdtemp()
    
    with app.test_client() as client:
        yield client
    
    # 清理
    import shutil
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    if os.path.exists(app.config['RESULTS_FOLDER']):
        shutil.rmtree(app.config['RESULTS_FOLDER'])


@pytest.fixture
def sample_image():
    """创建测试图片"""
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


class TestHealthAPI:
    """健康检查API测试"""
    
    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'message' in data


class TestUploadAPI:
    """文件上传API测试"""
    
    def test_upload_without_file(self, client):
        """测试无文件上传"""
        response = client.post('/api/upload')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_upload_empty_filename(self, client):
        """测试空文件名"""
        response = client.post('/api/upload', data={
            'file': (BytesIO(b''), '')
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_upload_invalid_file_type(self, client):
        """测试无效文件类型"""
        response = client.post('/api/upload', data={
            'file': (BytesIO(b'content'), 'test.txt')
        }, content_type='multipart/form-data')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_upload_valid_image(self, client, sample_image):
        """测试上传有效图片"""
        response = client.post('/api/upload', data={
            'file': (sample_image, 'test.png')
        }, content_type='multipart/form-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'filename' in data
        assert 'filepath' in data
        assert os.path.exists(data['filepath'])


class TestParseAPI:
    """表格解析API测试"""
    
    def test_parse_without_filename(self, client):
        """测试无文件名解析"""
        response = client.post('/api/parse', 
                             json={},
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_parse_nonexistent_file(self, client):
        """测试解析不存在的文件"""
        response = client.post('/api/parse',
                             json={'filename': 'nonexistent.jpg'},
                             content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_parse_valid_file(self, client, sample_image):
        """测试解析有效文件（需要mock模型）"""
        # 先上传文件
        upload_response = client.post('/api/upload', data={
            'file': (sample_image, 'test.png')
        }, content_type='multipart/form-data')
        
        upload_data = json.loads(upload_response.data)
        filename = upload_data['filename']
        
        # 尝试解析（可能会失败，因为模型未初始化，但应该返回合理的错误）
        response = client.post('/api/parse',
                             json={'filename': filename},
                             content_type='application/json')
        
        # 可能返回200（如果模型可用）或500（如果模型不可用）
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        
        if response.status_code == 200:
            assert data['success'] is True
            assert 'result' in data
        else:
            assert 'error' in data


class TestResultsAPI:
    """结果查询API测试"""
    
    def test_get_nonexistent_result(self, client):
        """测试获取不存在的结果"""
        response = client.get('/api/results/nonexistent.json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_existing_result(self, client):
        """测试获取存在的结果"""
        # 创建测试结果文件
        result_data = {'tables': [], 'total_tables': 0}
        result_path = os.path.join(app.config['RESULTS_FOLDER'], 'test_result.json')
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f)
        
        response = client.get('/api/results/test_result.json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'tables' in data
        assert data['total_tables'] == 0


class TestCORS:
    """CORS测试"""
    
    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options('/api/health')
        # Flask-CORS应该自动处理OPTIONS请求
        assert response.status_code in [200, 204]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
