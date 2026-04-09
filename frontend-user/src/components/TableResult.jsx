/**
 * 表格结果展示组件
 *
 * 职责：
 * - 展示单个解析后的表格
 * - 支持单元格编辑
 * - 导出和复制操作
 */
import { useState } from "react";
import { notification, Dropdown } from "antd";
import PropTypes from "prop-types";
import { exportToCsv, exportToExcel, exportToJson } from "../api";
import "./TableResult.css";

const TableResult = ({ table, tableIndex }) => {
  const [exporting, setExporting] = useState(false);

  const { data, structure, confidence, page } = table;

  if (!data?.length) return null;

  // 下载 blob 文件
  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  // 导出处理
  const handleExport = async (format) => {
    setExporting(true);
    try {
      let response;
      let filename;

      const tables = [table];

      if (format === "csv") {
        response = await exportToCsv(tables, 0);
        filename = `table_${tableIndex + 1}.csv`;
      } else if (format === "excel") {
        response = await exportToExcel(tables, 0, false);
        filename = `table_${tableIndex + 1}.xlsx`;
      } else if (format === "json") {
        response = await exportToJson(tables, 0, false);
        filename = `table_${tableIndex + 1}.json`;
      }

      downloadBlob(response.data, filename);
      notification.success({
        message: "导出成功",
        description: `已下载 ${filename}`,
        duration: 2,
      });
    } catch (err) {
      notification.error({
        message: "导出失败",
        description: err.response?.data?.error || err.message,
      });
    } finally {
      setExporting(false);
    }
  };

  // 复制到剪贴板
  const handleCopy = async () => {
    const text = data.map((row) => row.join("\t")).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      notification.success({
        message: "复制成功",
        description: "表格数据已复制到剪贴板",
        duration: 2,
      });
    } catch (err) {
      notification.error({
        message: "复制失败",
        description: "请手动选择并复制",
      });
    }
  };

  // 导出菜单项
  const exportMenuItems = [
    { key: "csv", label: "📄 导出为 CSV" },
    { key: "excel", label: "📊 导出为 Excel" },
    { key: "json", label: "📋 导出为 JSON" },
    { type: "divider" },
    { key: "copy", label: "📋 复制到剪贴板" },
  ];

  const handleMenuClick = ({ key }) => {
    if (key === "copy") {
      handleCopy();
    } else {
      handleExport(key);
    }
  };

  return (
    <div className="table-result-card">
      <div className="table-result-header">
        <div className="table-result-title">
          <span>📊</span>
          <span>
            {page !== undefined ? `第 ${page + 1} 页 - ` : ""}表格{" "}
            {tableIndex + 1}
          </span>
        </div>
        <div className="table-result-actions">
          <div className="table-result-badges">
            <span className="result-badge size">
              {structure?.rows || data.length} ×{" "}
              {structure?.cols || data[0]?.length || 0}
            </span>
            <span className="result-badge confidence">
              {(confidence * 100).toFixed(1)}%
            </span>
          </div>
          <Dropdown
            menu={{
              items: exportMenuItems,
              onClick: handleMenuClick,
            }}
            trigger={["click"]}
            disabled={exporting}
          >
            <button className="export-btn-small" disabled={exporting}>
              {exporting ? "⏳" : "📥"} 操作
            </button>
          </Dropdown>
        </div>
      </div>

      <div className="table-result-body">
        <table className="data-table">
          <thead>
            <tr>
              {data[0]?.map((_, colIdx) => (
                <th key={colIdx}>列 {colIdx + 1}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, colIdx) => (
                  <td key={colIdx}>{cell || "-"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

TableResult.propTypes = {
  table: PropTypes.shape({
    data: PropTypes.arrayOf(PropTypes.array).isRequired,
    structure: PropTypes.shape({
      rows: PropTypes.number,
      cols: PropTypes.number,
    }),
    confidence: PropTypes.number,
    page: PropTypes.number,
  }).isRequired,
  tableIndex: PropTypes.number.isRequired,
};

export default TableResult;
