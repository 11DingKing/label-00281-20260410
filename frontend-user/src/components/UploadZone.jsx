/**
 * 文件上传区域组件
 *
 * 职责：
 * - 文件拖拽上传
 * - 点击选择文件
 * - 文件类型和大小验证
 */
import { useState, useCallback } from "react";
import PropTypes from "prop-types";
import "./UploadZone.css";

const UploadZone = ({
  onFileSelect,
  accept = "image/*,.pdf",
  maxSize = 16 * 1024 * 1024,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = useCallback(
    (file) => {
      const isImage = file.type.startsWith("image/");
      const isPdf = file.type === "application/pdf";

      if (!isImage && !isPdf) {
        return { valid: false, error: `${file.name} 不是支持的格式` };
      }

      if (file.size > maxSize) {
        return {
          valid: false,
          error: `${file.name} 超过 ${Math.round(maxSize / 1024 / 1024)}MB 限制`,
        };
      }

      return { valid: true };
    },
    [maxSize],
  );

  const handleFiles = useCallback(
    (files) => {
      if (disabled) return;

      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;

      const file = fileArray[0];
      const validation = validateFile(file);

      if (validation.valid) {
        onFileSelect(file);
      } else {
        onFileSelect(null, validation.error);
      }
    },
    [disabled, validateFile, onFileSelect],
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleClick = useCallback(() => {
    if (disabled) return;
    document.getElementById("file-input-upload-zone").click();
  }, [disabled]);

  const handleInputChange = useCallback(
    (e) => {
      handleFiles(e.target.files);
      e.target.value = "";
    },
    [handleFiles],
  );

  return (
    <div
      className={`upload-zone ${isDragging ? "dragging" : ""} ${disabled ? "disabled" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        id="file-input-upload-zone"
        type="file"
        accept={accept}
        onChange={handleInputChange}
        style={{ display: "none" }}
        disabled={disabled}
      />
      <div className="upload-icon">📁</div>
      <div className="upload-title">点击或拖拽文件到此处</div>
      <div className="upload-hint">
        支持图片和 PDF 文件，最大 {Math.round(maxSize / 1024 / 1024)}MB
      </div>
      <div className="upload-formats">
        <span className="format-tag">PNG</span>
        <span className="format-tag">JPG</span>
        <span className="format-tag">PDF</span>
        <span className="format-tag">TIFF</span>
      </div>
    </div>
  );
};

UploadZone.propTypes = {
  onFileSelect: PropTypes.func.isRequired,
  accept: PropTypes.string,
  maxSize: PropTypes.number,
  disabled: PropTypes.bool,
};

export default UploadZone;
