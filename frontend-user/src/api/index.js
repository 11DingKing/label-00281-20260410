/**
 * API接口封装
 */
import axios from "axios";

// 在Docker环境中，API通过nginx代理，使用相对路径
// 在开发环境中，使用环境变量或默认值
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.MODE === "production" ? "/api" : "http://localhost:5000");

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时，因为解析可能需要较长时间
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      if (status === 500) {
        console.error("服务器错误:", data);
      } else if (status === 404) {
        console.error("资源未找到");
      }
    } else if (error.request) {
      console.error("网络错误，请检查后端服务是否启动");
    }
    return Promise.reject(error);
  },
);

export default api;

// API方法
export const healthCheck = () => {
  return api.get("/health");
};

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const parseTable = (filename) => {
  return api.post("/parse", { filename });
};

export const getResult = (filename) => {
  return api.get(`/results/${filename}`);
};

/**
 * 导出表格数据为 CSV 格式
 * @param {Array} tables - 表格数据数组
 * @param {number} tableIndex - 表格索引
 */
export const exportToCsv = (tables, tableIndex = 0) => {
  return api.post(
    "/export/csv",
    { tables, table_index: tableIndex },
    {
      responseType: "blob",
    },
  );
};

/**
 * 导出表格数据为 Excel 格式
 * @param {Array} tables - 表格数据数组
 * @param {number} tableIndex - 表格索引
 * @param {boolean} exportAll - 是否导出所有表格
 */
export const exportToExcel = (tables, tableIndex = 0, exportAll = false) => {
  return api.post(
    "/export/excel",
    { tables, table_index: tableIndex, export_all: exportAll },
    {
      responseType: "blob",
    },
  );
};

/**
 * 导出表格数据为 JSON 格式
 * @param {Array} tables - 表格数据数组
 * @param {number} tableIndex - 表格索引
 * @param {boolean} exportAll - 是否导出所有表格
 */
export const exportToJson = (tables, tableIndex = 0, exportAll = false) => {
  return api.post(
    "/export/json",
    { tables, table_index: tableIndex, export_all: exportAll },
    {
      responseType: "blob",
    },
  );
};

// ==================== 图片预览 API ====================

/**
 * 获取图片预览 URL
 */
export const getPreviewUrl = (filename) => {
  return `${API_BASE_URL}/preview/${filename}`;
};

/**
 * 获取带检测框的预览图
 */
export const getDetectPreview = (filename) => {
  return api.post("/detect-preview", { filename });
};

// ==================== 历史记录 API ====================

/**
 * 获取历史记录列表
 */
export const getHistory = (page = 1, perPage = 20) => {
  return api.get("/history", { params: { page, per_page: perPage } });
};

/**
 * 获取历史记录详情
 */
export const getHistoryDetail = (recordId) => {
  return api.get(`/history/${recordId}`);
};

/**
 * 删除历史记录
 */
export const deleteHistory = (recordId) => {
  return api.delete(`/history/${recordId}`);
};

/**
 * 清空历史记录
 */
export const clearHistory = () => {
  return api.post("/history/clear");
};

// ==================== 批量处理 API ====================

/**
 * 批量上传文件
 */
export const batchUpload = (files) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  return api.post("/batch/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

/**
 * 批量解析表格
 */
export const batchParse = (filenames) => {
  return api.post("/batch/parse", { filenames });
};
