/**
 * 文件预览组件
 *
 * 职责：
 * - 显示已选择的文件信息
 * - 提供删除/清空功能
 */
import PropTypes from "prop-types";
import "./FilePreview.css";

const FilePreview = ({ file, onRemove, disabled = false }) => {
  if (!file) return null;

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  const getFileIcon = (filename) => {
    const ext = filename.split(".").pop().toLowerCase();
    if (ext === "pdf") return "📄";
    if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) return "🖼️";
    return "📄";
  };

  return (
    <div className="file-preview">
      <div className="file-info">
        <div className="file-icon">{getFileIcon(file.name)}</div>
        <div className="file-details">
          <div className="file-name" title={file.name}>
            {file.name}
          </div>
          <div className="file-size">{formatFileSize(file.size)}</div>
        </div>
        {!disabled && (
          <button
            className="file-remove"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            title="移除文件"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};

FilePreview.propTypes = {
  file: PropTypes.shape({
    name: PropTypes.string.isRequired,
    size: PropTypes.number.isRequired,
    type: PropTypes.string,
  }),
  onRemove: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default FilePreview;
