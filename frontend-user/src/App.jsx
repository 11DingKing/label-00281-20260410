import React, { useState, useEffect } from 'react'
import { Layout } from 'antd'
import { healthCheck } from './api'
import TableParser from './components/TableParser'
import './App.css'

const { Header, Content } = Layout

function App() {
  const [serviceStatus, setServiceStatus] = useState('checking')

  useEffect(() => {
    checkServiceStatus()
  }, [])

  const checkServiceStatus = async () => {
    try {
      const response = await healthCheck()
      if (response.data.status === 'ok') {
        setServiceStatus('online')
      }
    } catch (err) {
      setServiceStatus('offline')
    }
  }

  const getStatusText = () => {
    switch (serviceStatus) {
      case 'online': return 'AI 服务在线'
      case 'offline': return '服务离线'
      default: return '检测中...'
    }
  }

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo-container">
              <div className="logo-icon">
                <span role="img" aria-label="table">⚡</span>
              </div>
              <div className="logo-text">
                <h1 className="logo-title">TableAI</h1>
                <p className="logo-subtitle">智能表格识别引擎</p>
              </div>
            </div>
          </div>
          <div className="header-right">
            <div className="status-badge" onClick={checkServiceStatus} style={{ cursor: 'pointer' }}>
              <span className={`status-dot ${serviceStatus}`}></span>
              <span>{getStatusText()}</span>
            </div>
          </div>
        </div>
      </Header>
      <Content className="app-content">
        <TableParser serviceStatus={serviceStatus} onRetryConnection={checkServiceStatus} />
      </Content>
    </Layout>
  )
}

export default App
