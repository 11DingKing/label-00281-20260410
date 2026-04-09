import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { message, notification } from 'antd'
import TableParser from '../TableParser'
import * as api from '../../api'

// Mock API
vi.mock('../../api', () => ({
  healthCheck: vi.fn(),
  uploadFile: vi.fn(),
  parseTable: vi.fn(),
}))

// Mock Ant Design
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
    notification: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  }
})

describe('TableParser组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该渲染组件', () => {
    render(<TableParser />)
    expect(screen.getByText(/上传文件/i)).toBeInTheDocument()
    expect(screen.getByText(/解析结果/i)).toBeInTheDocument()
  })

  it('应该检查服务状态', async () => {
    api.healthCheck.mockResolvedValue({
      data: { status: 'ok', message: '服务正常' }
    })

    render(<TableParser />)

    await waitFor(() => {
      expect(api.healthCheck).toHaveBeenCalled()
    })
  })

  it('应该处理服务连接失败', async () => {
    api.healthCheck.mockRejectedValue(new Error('连接失败'))

    render(<TableParser />)

    await waitFor(() => {
      expect(notification.error).toHaveBeenCalled()
    })
  })

  it('应该显示文件上传区域', () => {
    render(<TableParser />)
    const uploadText = screen.getByText(/点击或拖拽文件到此区域上传/i)
    expect(uploadText).toBeInTheDocument()
  })

  it('应该显示开始解析按钮', () => {
    render(<TableParser />)
    const parseButton = screen.getByText(/开始解析/i)
    expect(parseButton).toBeInTheDocument()
  })

  it('应该在无文件时禁用解析按钮', () => {
    render(<TableParser />)
    const parseButton = screen.getByText(/开始解析/i).closest('button')
    expect(parseButton).toBeDisabled()
  })
})
