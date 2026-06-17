我来为你编写一个详细的 README 文件。首先让我了解一下项目的更多信息：




# AI 招聘管理系统

基于 Flask 的智能招聘管理平台，集成 AI 简历分析功能，支持多 AI 后端（通义千问/本地 RAGFlow），实现职位发布、简历上传、智能匹配和申请审核的全流程管理。

## 🌟 核心功能

### 用户功能
- 👤 **用户注册/登录** - 支持新用户注册和身份认证
- 📄 **简历上传** - 支持 PDF、Word (.doc/.docx) 格式简历
- 🔍 **职位浏览** - 查看所有开放职位及详细信息
- 📝 **职位申请** - 在线申请职位并上传简历
- 📊 **申请跟踪** - 查看个人申请状态和历史记录

### 管理员功能
- 📋 **职位管理** - 发布、编辑和管理招聘职位
- ✅ **申请审核** - 审核用户申请（通过/拒绝/待审核）
- 📈 **数据统计** - 可视化展示申请数量、部门分布等数据
- 👥 **用户管理** - 查看所有注册用户信息

### AI 智能分析
- 🤖 **简历智能匹配** - AI 自动分析简历与职位的匹配度
- 💡 **技能识别** - 自动提取匹配技能和缺失技能
- 📊 **匹配评分** - 0-100 分量化匹配程度
- 🔄 **多后端支持** - 支持阿里云通义千问和本地 RAGFlow/Ollama

## 🛠️ 技术栈

### 后端框架
- **Flask** - Python Web 框架
- **Flask-SQLAlchemy** - ORM 数据库管理
- **MySQL** - 关系型数据库

### AI 与文档处理
- **OpenAI SDK** - 调用通义千问 API
- **RAGFlow** - 本地 AI 知识库引擎
- **PyPDF2** - PDF 文档解析
- **python-docx** - Word 文档解析

### 前端技术
- **HTML5/CSS3** - 页面结构与样式
- **Jinja2** - 模板引擎
- **Bootstrap** - UI 组件库（如使用）

### 其他工具
- **Werkzeug** - 密码哈希与安全工具
- **Requests** - HTTP 客户端

## 📦 安装与配置

### 前置要求
- Python 3.8+
- MySQL 5.7+ 或 MariaDB
- Git

### 快速开始

#### 1. 克隆项目
```
bash
git clone https://github.com/Yushe25/ai_web001.git
cd ai_web001
```
#### 2. 创建虚拟环境
```
bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```
#### 3. 安装依赖
```
bash
pip install flask flask-sqlalchemy pymysql openai requests PyPDF2 python-docx
```
#### 4. 配置环境变量（可选但推荐）

创建 `.env` 文件（不会被提交到 Git）：

```
env
# 数据库配置
DATABASE_URL=mysql+pymysql://root:your_password@localhost/web_test

# AI 配置
QWEN_API_KEY=your_qwen_api_key
QWEN_MODEL=qwen-turbo
RAGFLOW_API_KEY=your_ragflow_api_key
RAGFLOW_BASE_URL=http://localhost:9380/api/v1

# AI 后端选择 (qwen 或 local)
AI_BACKEND=qwen
```
#### 5. 修改数据库配置

编辑 `app.py` 第 21 行，修改为你的 MySQL 连接信息：

```
python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://用户名:密码@localhost/数据库名'
```
> ⚠️ **安全提示**: 建议使用环境变量存储敏感信息，不要将密码硬编码在代码中。

#### 6. 初始化数据库并运行
```
bash
python app.py
```
首次运行会自动：
- 创建数据库表结构
- 初始化管理员账号（用户名: `admin`, 密码: `admin123`）
- 添加示例用户和职位数据

访问 http://127.0.0.1:5000 即可使用系统。

## 📁 项目结构

```

ai_web001/
├── app.py                  # Flask 主应用入口
├── ai_select.py            # AI 简历分析器核心逻辑
├── local_ai.py             # RAGFlow 本地 AI 客户端
├── templates/              # HTML 模板目录
│   ├── base.html          # 基础模板
│   ├── login.html         # 登录页面
│   ├── register.html      # 注册页面
│   ├── admin_dashboard.html  # 管理员仪表板
│   ├── user_dashboard.html   # 用户仪表板
│   ├── about.html         # 关于我们
│   └── help.html          # 帮助中心
├── static/                 # 静态资源目录
│   ├── css/               # 样式文件
│   │   └── style.css
│   ├── images/            # 图片资源
│   └── uploads/           # 用户上传的简历文件
├── test_uploads/          # 测试上传目录
├── .gitignore             # Git 忽略配置
└── README.md              # 项目说明文档
```
## 🎯 使用说明

### 普通用户

1. **注册账号** - 访问 `/register` 页面注册新用户
2. **登录系统** - 使用注册的账号登录
3. **浏览职位** - 在仪表板查看所有开放职位
4. **申请职位** - 点击申请职位，上传简历（PDF/Word）
5. **查看状态** - 在申请记录中查看审核状态

### 管理员

1. **登录管理员账号**
   - 用户名: `admin`
   - 密码: `admin123`（建议首次登录后修改）

2. **发布职位**
   - 填写职位名称、部门、薪资、描述和要求
   - 点击发布按钮

3. **审核申请**
   - 查看所有用户的申请记录
   - 选择"通过"、"拒绝"或"待审核"

4. **查看统计**
   - 职位申请数量统计
   - 部门分布分析
   - 申请状态概览

### AI 简历分析

系统提供两种 AI 后端选项：

#### 方式一：阿里云通义千问（默认）
- 需要申请阿里云 DashScope API Key
- 配置 `QWEN_API_KEY` 环境变量
- 设置 `AI_BACKEND=qwen`

#### 方式二：本地 RAGFlow/Ollama
- 部署本地 RAGFlow 服务
- 配置 `RAGFLOW_API_KEY` 和 `RAGFLOW_BASE_URL`
- 设置 `AI_BACKEND=local`

API 端点：`POST /ai`

请求参数：
```
json
{
  "job_description": "职位描述文本",
  "resume_file_path": "简历文件路径"
}
```
响应示例：
```
json
{
  "match_score": 85,
  "matched_skills": ["Python", "Flask", "MySQL"],
  "missing_skills": ["Docker", "Redis"],
  "summary": "候选人具备扎实的后端开发技能...",
  "analyzed_at": "2026-06-17T10:30:00",
  "backend_used": "qwen"
}
```
## 🔐 安全特性

- ✅ **密码加密** - 采用 PBKDF2-SHA256 算法进行密码哈希存储
- ✅ **会话管理** - 基于 Session 的用户认证机制
- ✅ **文件上传验证** - 限制文件类型和大小（最大 16MB）
- ✅ **权限控制** - 区分普通用户和管理员权限
- ✅ **CSRF 保护** - Flask 内置 CSRF 防护

> ⚠️ **注意**: 当前版本密码验证仍使用明文对比，计划升级为 `werkzeug.security` 的安全哈希验证。

## 🧪 测试

运行单元测试：
```
bash
pytest
```
## 📝 开发规范

### 日志记录
系统使用 Python `logging` 模块，配置如下：
- 级别: `INFO`
- 格式: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### 代码风格
- 遵循 PEP 8 Python 编码规范
- 函数和类使用清晰的命名
- 关键业务逻辑添加注释说明

## 🚀 部署建议

### 生产环境配置

1. **使用 Gunicorn 作为 WSGI 服务器**
```
bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
2. **配置 Nginx 反向代理**

3. **使用 HTTPS**

4. **启用数据库连接池**

5. **配置日志轮转**

6. **定期备份数据库**

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request


## 📞 联系方式

- GitHub: [@Yushe25](https://github.com/Yushe25)
- Email: yushang2575@163.com

## 🙏 致谢

感谢以下开源项目：
- [Flask](https://flask.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [RAGFlow](https://github.com/infiniflow/ragflow)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
