import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import api, { healthCheck, uploadFile, parseTable, getResult } from '../index'

// Mock axios
vi.mock('axios', () => {
  const actualAxios = vi.importActual('axios')
  return {
    ...actualAxios,
    default: {
      create: vi.fn(() => ({
        get: vi.fn(),
        post: vi.fn(),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() }
        }
      })),
      get: vi.fn(),
      post: vi.fn(),
    }
  }
})

describe('API模块', () => {
  let mockGet, mockPost

  beforeEach(() => {
    vi.clearAllMocks()
    // 创建mock函数
    mockGet = vi.fn()
    mockPost = vi.fn()
    
    // Mock api实例的方法
    api.get = mockGet
    api.post = mockPost
  })

  describe('healthCheck', () => {
    it('应该成功调用健康检查接口', async () => {
      const mockResponse = {
        data: {
          status: 'ok',
          message: '表格解析服务运行正常'
        }
      }
      mockGet.mockResolvedValue(mockResponse)

      const result = await healthCheck()

      expect(mockGet).toHaveBeenCalledWith('/api/health')
      expect(result.data.status).toBe('ok')
    })

    it('应该处理健康检查失败', async () => {
      const mockError = new Error('Network Error')
      mockGet.mockRejectedValue(mockError)

      await expect(healthCheck()).rejects.toThrow()
    })
  })

  describe('uploadFile', () => {
    it('应该成功上传文件', async () => {
      const mockFile = new File(['content'], 'test.png', { type: 'image/png' })
      const mockResponse = {
        data: {
          success: true,
          filename: '20240101_120000_test.png',
          filepath: '/uploads/20240101_120000_test.png'
        }
      }
      mockPost.mockResolvedValue(mockResponse)

      const result = await uploadFile(mockFile)

      expect(mockPost).toHaveBeenCalledWith(
        '/api/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      )
      expect(result.data.success).toBe(true)
      expect(result.data.filename).toBeDefined()
    })

    it('应该处理上传失败', async () => {
      const mockFile = new File(['content'], 'test.png', { type: 'image/png' })
      const mockError = {
        response: {
          data: {
            error: '上传失败'
          }
        }
      }
      mockPost.mockRejectedValue(mockError)

      await expect(uploadFile(mockFile)).rejects.toThrow()
    })
  })

  describe('parseTable', () => {
    it('应该成功解析表格', async () => {
      const mockResponse = {
        data: {
          success: true,
          result: {
            tables: [],
            total_tables: 0
          }
        }
      }
      mockPost.mockResolvedValue(mockResponse)

      const result = await parseTable('test.png')

      expect(mockPost).toHaveBeenCalledWith(
        '/api/parse',
        { filename: 'test.png' },
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json'
          }
        })
      )
      expect(result.data.success).toBe(true)
      expect(result.data.result).toBeDefined()
    })

    it('应该处理解析失败', async () => {
      const mockError = {
        response: {
          data: {
            error: '解析失败'
          }
        }
      }
      mockPost.mockRejectedValue(mockError)

      await expect(parseTable('test.png')).rejects.toThrow()
    })
  })

  describe('getResult', () => {
    it('应该成功获取结果', async () => {
      const mockResponse = {
        data: {
          tables: [],
          total_tables: 0
        }
      }
      mockGet.mockResolvedValue(mockResponse)

      const result = await getResult('result_test.json')

      expect(mockGet).toHaveBeenCalledWith('/api/results/result_test.json')
      expect(result.data).toBeDefined()
    })

    it('应该处理获取结果失败', async () => {
      const mockError = {
        response: {
          status: 404,
          data: {
            error: '结果文件不存在'
          }
        }
      }
      mockGet.mockRejectedValue(mockError)

      await expect(getResult('nonexistent.json')).rejects.toThrow()
    })
  })
})
