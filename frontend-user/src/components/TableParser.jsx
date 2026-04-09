/**
 * 表格解析主组件
 *
 * 职责：
 * - 协调各子组件的交互
 * - 管理应用状态
 * - 处理解析流程
 *
 * 子组件：
 * - UploadZone: 文件上传区域
 * - FilePreview: 文件预览
 * - TableResult: 表格结果展示
 */
import { useState, useCallback } from "react";
import { notification, Modal } from "antd";
import PropTypes from "prop-types";

import { uploadFile, parseTable, getDetectPreview } from "../api";

// 子组件
import UploadZone from "./UploadZone";
import FilePreview from "./FilePreview";
import TableResult from "./TableResult";

import "./TableParser.css";

const TableParser = ({ serviceStatus, onRetryConnection }) => {
  // ==================== 状态管理 ====================

  // 文件状态
  const [selectedFile, setSelectedFile] = useState(null);

  // 解析状态
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [parseProgress, setParseProgress] = useState(0);
  const [parseStatus, setParseStatus] = useState(""); // 当前处理阶段
  const [estimatedTime, setEstimatedTime] = useState(null); // 预计剩余时间

  // 结果状态
  const [parseResult, setParseResult] = useState(null);
  const [error, setError] = useState(null);

  // UI 状态
  const [modalVisible, setModalVisible] = useState(false);

  // 预览状态
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // ==================== 事件处理 ====================

  // 文件选择
  const handleFileSelect = useCallback((file, error) => {
    if (error) {
      notification.warning({
        message: "文件选择失败",
        description: error,
      });
      return;
    }

    setSelectedFile(file);
    setParseResult(null);
    setError(null);

    notification.success({
      message: "文件已选择",
      description: file.name,
      duration: 2,
    });
  }, []);

  // 清除文件
  const handleClearFile = useCallback(() => {
    setSelectedFile(null);
    setParseResult(null);
    setError(null);
  }, []);

  // 解析表格
  const handleParse = useCallback(async () => {
    if (!selectedFile) {
      notification.warning({
        message: "请先选择文件",
        description: "请上传需要解析的表格图片或 PDF",
      });
      return;
    }

    setUploading(true);
    setError(null);
    setParseResult(null);
    setUploadProgress(0);
    setParseProgress(0);

    try {
      // 上传文件 - 快速递增到90%
      const uploadInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 15, 90));
      }, 150);

      const uploadResponse = await uploadFile(selectedFile);
      clearInterval(uploadInterval);
      setUploadProgress(100);

      if (!uploadResponse.data.success) {
        throw new Error(uploadResponse.data.error || "上传失败");
      }

      // 检查 PDF 页数警告
      const pdfInfo = uploadResponse.data.pdf_info;
      const pageCount = pdfInfo?.total_pages || 1;
      
      if (pdfInfo?.slow_warning) {
        notification.warning({
          message: "PDF 页数较多",
          description: `该 PDF 共 ${pageCount} 页，处理可能需要较长时间`,
          duration: 6,
        });
      }

      // 解析表格
      setUploading(false);
      setLoading(true);
      setParseStatus("正在检测表格...");
      
      // 计算预计时间：每页约 5 秒
      const isPdf = selectedFile.name.toLowerCase().endsWith(".pdf");
      const totalEstimatedSeconds = isPdf ? pageCount * 5 : 5;
      let remainingSeconds = totalEstimatedSeconds;
      setEstimatedTime(remainingSeconds);

      // 进度和时间更新
      const startTime = Date.now();
      const parseInterval = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        
        // 更新进度
        setParseProgress((prev) => {
          if (prev < 30) return prev + 3;
          if (prev < 60) return prev + 1.5;
          if (prev < 90) return prev + 0.3;
          return prev;
        });
        
        // 更新剩余时间
        remainingSeconds = Math.max(0, totalEstimatedSeconds - elapsed);
        setEstimatedTime(Math.ceil(remainingSeconds));
        
        // 更新状态文字
        if (elapsed < totalEstimatedSeconds * 0.3) {
          setParseStatus("正在检测表格...");
        } else if (elapsed < totalEstimatedSeconds * 0.6) {
          setParseStatus("正在解析结构...");
        } else {
          setParseStatus("正在识别文字...");
        }
      }, 500);

      const parseResponse = await parseTable(uploadResponse.data.filename);
      clearInterval(parseInterval);
      setParseProgress(100);
      setParseStatus("完成");
      setEstimatedTime(0);

      if (parseResponse.data.success) {
        const result = parseResponse.data.result;
        setParseResult(result);
        setModalVisible(true);

        // 检查是否有慢速警告
        if (result?.slow_warning) {
          notification.info({
            message: "处理完成",
            description: `PDF 共 ${result.total_pages} 页，已全部处理完成`,
            duration: 5,
          });
        }

        notification.success({
          message: "解析完成",
          description: `成功识别 ${result?.total_tables || 0} 个表格`,
        });
      } else {
        throw new Error(parseResponse.data.error || "解析失败");
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message || "处理失败";
      setError(errorMsg);
      notification.error({
        message: "处理失败",
        description: errorMsg,
      });
    } finally {
      setUploading(false);
      setLoading(false);
      setTimeout(() => {
        setUploadProgress(0);
        setParseProgress(0);
      }, 800);
    }
  }, [selectedFile]);

  // 预览检测结果
  const handlePreview = useCallback(async () => {
    if (!selectedFile) {
      notification.warning({ message: "请先选择文件" });
      return;
    }

    setPreviewLoading(true);
    try {
      const uploadResponse = await uploadFile(selectedFile);
      if (uploadResponse.data.success) {
        const previewResponse = await getDetectPreview(
          uploadResponse.data.filename,
        );
        if (previewResponse.data.success) {
          setPreviewData(previewResponse.data);
          setPreviewVisible(true);
        }
      }
    } catch (err) {
      notification.error({
        message: "预览失败",
        description: err.response?.data?.error || err.message,
      });
    } finally {
      setPreviewLoading(false);
    }
  }, [selectedFile]);

  // ==================== 渲染辅助 ====================

  const tables = parseResult?.tables || [];

  // ==================== 渲染 ====================

  return (
    <div className="table-parser">
      {/* Hero Section */}
      <div className="hero-section">
        <h1 className="hero-title">智能表格识别</h1>
        <p className="hero-subtitle">
          上传表格图片或 PDF，AI 自动识别表格结构并提取数据
        </p>
        <div className="hero-badges">
          <span className="tech-badge">
            <span className="tech-badge-icon">🎯</span>
            YOLOv8 检测
          </span>
          <span className="tech-badge">
            <span className="tech-badge-icon">🧠</span>
            PubTabNet
          </span>
          <span className="tech-badge">
            <span className="tech-badge-icon">👁️</span>
            PaddleOCR
          </span>
        </div>
      </div>

      {/* 离线提示 */}
      {serviceStatus === "offline" && (
        <div className="offline-banner">
          <div className="offline-content">
            <span className="offline-icon">⚠️</span>
            <div className="offline-text">
              <h4>服务未连接</h4>
              <p>无法连接到后端服务，请确保服务已启动</p>
            </div>
          </div>
          <button className="retry-button" onClick={onRetryConnection}>
            重试连接
          </button>
        </div>
      )}

      {/* 主内容区 */}
      <div className="parser-container-single">
        <div className="glass-card">
          <div className="card-body">
            {/* 上传区域 */}
            <UploadZone
              onFileSelect={handleFileSelect}
              disabled={uploading || loading}
            />

            {/* 已选文件预览 */}
            <FilePreview
              file={selectedFile}
              onRemove={handleClearFile}
              disabled={uploading || loading}
            />

                    {/* 进度条 */}
                    {(uploading || loading) && (
                      <div className="progress-section">
                        {uploading && (
                          <div className="progress-item">
                            <div className="progress-label">
                              <span>上传中...</span>
                              <span>{uploadProgress}%</span>
                            </div>
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${uploadProgress}%` }}
                              />
                            </div>
                          </div>
                        )}
                        {loading && (
                          <div className="progress-item">
                            <div className="progress-label">
                              <span>{parseProgress >= 90 ? "即将完成，请耐心等待..." : (parseStatus || "AI 解析中...")}</span>
                              <span className="progress-info">
                                <span className="progress-percent">
                                  {Math.round(parseProgress)}%
                                </span>
                                {estimatedTime > 0 && parseProgress < 90 && (
                                  <span className="progress-time">
                                    约 {estimatedTime}s
                                  </span>
                                )}
                              </span>
                            </div>
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${parseProgress}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 操作按钮 */}
                    <div className="action-buttons">
                      <button
                        className="preview-button"
                        onClick={handlePreview}
                        disabled={
                          !selectedFile ||
                          previewLoading ||
                          serviceStatus === "offline"
                        }
                      >
                        {previewLoading ? "⏳ 检测中..." : "👁️ 预览检测"}
                      </button>
                      <button
                        className="parse-button"
                        onClick={handleParse}
                        disabled={
                          !selectedFile ||
                          uploading ||
                          loading ||
                          serviceStatus === "offline"
                        }
                      >
                        {uploading
                          ? "⏳ 上传中..."
                          : loading
                            ? "🔄 解析中..."
                            : "⚡ 开始解析"}
                      </button>
                    </div>

                    {/* 功能介绍 */}
                    <div className="features-grid">
                      <div className="feature-card">
                        <div className="feature-icon">🎯</div>
                        <div className="feature-title">精准检测</div>
                        <div className="feature-desc">YOLOv8 深度学习模型</div>
                      </div>
                      <div className="feature-card">
                        <div className="feature-icon">🧠</div>
                        <div className="feature-title">智能解析</div>
                        <div className="feature-desc">PubTabNet 结构识别</div>
                      </div>
                      <div className="feature-card">
                        <div className="feature-icon">📄</div>
                        <div className="feature-title">多页PDF</div>
                        <div className="feature-desc">支持批量页面处理</div>
                      </div>
                      <div className="feature-card">
                        <div className="feature-icon">📊</div>
                        <div className="feature-title">多格式导出</div>
                        <div className="feature-desc">Excel / CSV / JSON</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

      {/* 预览弹窗 */}
      <Modal
        title="检测预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        className="result-modal"
        centered
      >
        {previewData?.previews?.map((preview, idx) => (
          <div key={idx} className="preview-page">
            <div className="preview-page-header">
              第 {preview.page + 1} 页 - 检测到 {preview.tables_count} 个表格
            </div>
            <img
              src={preview.image}
              alt={`Page ${preview.page + 1}`}
              className="preview-image"
            />
          </div>
        ))}
      </Modal>

      {/* 结果弹窗 */}
      <Modal
        title={
          <div className="modal-title">
            <span>📋</span>
            <span>解析结果</span>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={900}
        className="result-modal"
        centered
      >
        {error && (
          <div className="error-alert">
            <span className="error-icon">❌</span>
            <div className="error-content">
              <div className="error-title">解析失败</div>
              <div className="error-message">{error}</div>
            </div>
          </div>
        )}

        {parseResult && (
          <div className="modal-content">
            <div className="success-alert">
              <span className="success-icon">✅</span>
              <span className="success-text">
                成功解析 {parseResult.total_tables || 0} 个表格
                {parseResult.total_pages > 1 &&
                  ` (${parseResult.total_pages} 页)`}
              </span>
            </div>

            {parseResult.total_tables > 0 && (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{parseResult.total_tables}</div>
                  <div className="stat-label">表格数量</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {parseResult.total_pages || 1}
                  </div>
                  <div className="stat-label">页数</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {tables.reduce((sum, t) => sum + (t.data?.length || 0), 0)}
                  </div>
                  <div className="stat-label">总行数</div>
                </div>
              </div>
            )}

            <div className="modal-tables">
              {tables.length > 0 ? (
                tables.map((table, idx) => (
                  <TableResult key={idx} table={table} tableIndex={idx} />
                ))
              ) : (
                <div className="result-empty">
                  <div className="empty-icon">📭</div>
                  <div className="empty-title">未检测到表格</div>
                  <div className="empty-desc">请尝试上传更清晰的表格图片</div>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

TableParser.propTypes = {
  serviceStatus: PropTypes.string,
  onRetryConnection: PropTypes.func,
};

export default TableParser;
