# 小学知识查漏补缺系统（MVP）

这是一个可直接部署运行的 Web 系统，面向**深圳小学四年级下学期数学**，实现了：

- 创建学生档案
- 生成 20 题诊断卷
- 自动判分与错题分析
- 按知识点识别薄弱点
- 生成补弱训练卷
- 记录学生知识点掌握档案

## 技术栈

- FastAPI
- SQLite
- Jinja2 + 原生 JavaScript

## 目录结构

```bash
edu_diagnosis_web/
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   ├── question_bank.py
│   └── services.py
├── data/
│   └── app.db               # 首次运行后自动生成
├── static/
│   ├── app.js
│   └── styles.css
├── templates/
│   └── index.html
├── requirements.txt
└── README.md
```

## 本地运行

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器访问：

```text
http://127.0.0.1:8000
```

## 服务器部署（Ubuntu + systemd 示例）

### 1. 上传代码

把整个目录上传到服务器，例如：

```bash
/opt/edu_diagnosis_web
```

### 2. 安装 Python 和 venv

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd /opt/edu_diagnosis_web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 测试启动

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 配置 systemd

创建文件：

```bash
sudo nano /etc/systemd/system/edu-diagnosis.service
```

写入：

```ini
[Unit]
Description=Edu Diagnosis FastAPI App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/edu_diagnosis_web
Environment="PATH=/opt/edu_diagnosis_web/.venv/bin"
ExecStart=/opt/edu_diagnosis_web/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

然后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable edu-diagnosis
sudo systemctl start edu-diagnosis
sudo systemctl status edu-diagnosis
```

## Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 当前已实现的接口

### 创建学生

```http
POST /api/student/create
```

### 生成诊断卷

```http
POST /api/paper/generate
```

### 提交试卷并获取分析

```http
POST /api/paper/submit
```

### 生成补弱卷

```http
POST /api/paper/reinforce
```

### 查看学生知识点档案

```http
GET /api/student/{student_id}/dashboard
```

## 后续建议

下一阶段你可以继续扩展：

1. 增加语文、英语学科
2. 增加更多年级和教材版本
3. 接入 AI 生成变式题
4. 加入登录系统和家长端报告
5. 加入图片题和打印试卷导出

