# 前端用户端文档

## 项目简介

表格数据解析系统的前端用户界面，基于React和Ant Design构建，提供友好的表格解析交互体验。

## 技术栈

- **框架**: React 18
- **UI组件库**: Ant Design 5
- **构建工具**: Vite 5
- **HTTP客户端**: Axios
- **测试框架**: Vitest

## 快速开始

### 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 开发模式

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

### Docker运行

```bash
docker build -t table-parser-frontend-user .
docker run -p 8081:80 table-parser-frontend-user
```

## 项目结构

```
frontend-user/
├── src/
│   ├── main.jsx              # 入口文件
│   ├── App.jsx               # 主应用组件
│   ├── App.css               # 主应用样式
│   ├── index.css             # 全局样式
│   ├── api/                  # API封装
│   │   ├── index.js
│   │   └── __tests__/
│   ├── components/           # React组件
│   │   ├── TableParser.jsx
│   │   └── __tests__/
│   └── test/                 # 测试配置
├── public/                   # 静态资源
├── package.json              # 项目配置
├── vite.config.js            # Vite配置
└── Dockerfile               # Docker配置
```

## 功能特性

### 核心功能

1. **文件上传**
   - 支持拖拽上传
   - 支持点击选择
   - 文件类型验证
   - 文件大小限制（16MB）

2. **图片预览**
   - 实时预览上传的图片
   - 支持点击放大查看

3. **表格解析**
   - 一键解析表格
   - 实时进度显示
   - 解析结果展示

4. **结果展示**
   - 表格数据可视化
   - 统计信息展示
   - 多表格支持

### UI特性

- 现代化设计风格
- 响应式布局
- 流畅的动画效果
- Toast通知提示
- 进度条显示

## 配置说明

### 环境变量

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:5000
```

### Vite配置

在 `vite.config.js` 中可以修改：
- 开发服务器端口：默认 3000
- API代理地址：默认 `http://localhost:5000`
- 构建输出目录：默认 `dist`

## API集成

前端通过 `src/api/index.js` 封装所有API调用：

- `healthCheck()`: 健康检查
- `uploadFile(file)`: 上传文件
- `parseTable(filename)`: 解析表格
- `getResult(filename)`: 获取结果

## 测试

### 运行测试

```bash
npm run test
```

### 测试UI

```bash
npm run test:ui
```

### 覆盖率

```bash
npm run test:coverage
```

## 开发指南

### 代码规范

- 使用ESLint进行代码检查
- 遵循React Hooks最佳实践
- 组件化开发

### 样式规范

- 使用CSS Modules或styled-components
- 遵循Ant Design设计规范
- 响应式设计

### 组件开发

1. 创建组件文件
2. 编写组件逻辑
3. 添加样式
4. 编写测试用例
5. 更新文档

## 部署

### 静态部署

构建后，将 `dist/` 目录部署到静态服务器（Nginx、Apache等）

### Docker部署

```bash
docker build -t table-parser-frontend-user .
docker run -d -p 8081:80 table-parser-frontend-user
```

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:5000;
    }
}
```

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## 性能优化

1. 代码分割和懒加载
2. 图片优化和压缩
3. Gzip压缩
4. CDN加速
5. 缓存策略

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查后端服务是否启动
   - 检查API地址配置
   - 检查CORS设置

2. **构建失败**
   - 清除node_modules重新安装
   - 检查Node.js版本（>=16）
   - 检查依赖版本冲突

3. **样式问题**
   - 检查Ant Design版本
   - 检查CSS导入顺序
   - 清除浏览器缓存

## 许可证

MIT License
