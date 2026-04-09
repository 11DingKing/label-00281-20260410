/**
 * 历史记录面板组件
 *
 * 职责：
 * - 显示解析历史列表
 * - 查看/删除/清空历史记录
 */
import { useState, useEffect, useCallback } from "react";
import { notification, Popconfirm } from "antd";
import PropTypes from "prop-types";
import {
  getHistory,
  getHistoryDetail,
  deleteHistory,
  clearHistory,
} from "../api";
import "./HistoryPanel.css";

const HistoryPanel = ({ visible, onViewResult }) => {
  const [historyList, setHistoryList] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    const startTime = Date.now();
    try {
      const response = await getHistory(1, 50);
      if (response.data.success) {
        setHistoryList(response.data.history);
      }
    } catch (err) {
      console.error("加载历史记录失败:", err);
    } finally {
      // 最少显示 500ms 加载状态，避免闪烁
      const elapsed = Date.now() - startTime;
      const minDelay = 500;
      if (elapsed < minDelay) {
        setTimeout(() => setLoading(false), minDelay - elapsed);
      } else {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (visible) {
      loadHistory();
    }
  }, [visible, loadHistory]);

  const handleView = async (record) => {
    try {
      const response = await getHistoryDetail(record.id);
      if (response.data.success && response.data.record.result) {
        onViewResult(response.data.record.result);
      }
    } catch (err) {
      notification.error({ message: "加载失败" });
    }
  };

  const handleDelete = async (recordId) => {
    try {
      await deleteHistory(recordId);
      notification.success({ message: "删除成功" });
      loadHistory();
    } catch (err) {
      notification.error({ message: "删除失败" });
    }
  };

  const handleClear = async () => {
    try {
      await clearHistory();
      notification.success({ message: "历史记录已清空" });
      setHistoryList([]);
    } catch (err) {
      notification.error({ message: "清空失败" });
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="history-panel">
      <div className="history-header">
        <h3>解析历史</h3>
        {historyList.length > 0 && (
          <Popconfirm
            title="确定清空所有历史记录？"
            onConfirm={handleClear}
            okText="确定"
            cancelText="取消"
          >
            <button className="clear-history-btn">清空历史</button>
          </Popconfirm>
        )}
      </div>

      {loading ? (
        <div className="history-loading">
          <div className="loading-spinner" />
          <div>加载中...</div>
        </div>
      ) : historyList.length === 0 ? (
        <div className="history-empty">
          <div className="empty-icon">📭</div>
          <div className="empty-title">暂无历史记录</div>
          <div className="empty-desc">解析结果将自动保存到这里</div>
        </div>
      ) : (
        <div className="history-list">
          {historyList.map((record) => (
            <div key={record.id} className="history-item">
              <div className="history-info">
                <div className="history-name">{record.original_name}</div>
                <div className="history-meta">
                  <span>📊 {record.total_tables} 个表格</span>
                  <span>📄 {record.total_pages || 1} 页</span>
                  <span>🕐 {formatDate(record.created_at)}</span>
                </div>
              </div>
              <div className="history-actions">
                <button className="view-btn" onClick={() => handleView(record)}>
                  查看
                </button>
                <Popconfirm
                  title="确定删除此记录？"
                  onConfirm={() => handleDelete(record.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <button className="delete-btn">删除</button>
                </Popconfirm>
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="refresh-btn" onClick={loadHistory} disabled={loading}>
        <span className="refresh-icon">{loading ? "⏳" : "🔄"}</span>
        <span>{loading ? "刷新中..." : "刷新列表"}</span>
      </button>
    </div>
  );
};

HistoryPanel.propTypes = {
  visible: PropTypes.bool.isRequired,
  onViewResult: PropTypes.func.isRequired,
};

export default HistoryPanel;
