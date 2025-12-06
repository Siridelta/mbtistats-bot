# 1. 只有 Docker 才能让你在腾讯云上跑 Python 3.13
# 使用 slim-bookworm (Debian 12)，它比 oldstable 更适合跑新版 Chrome
FROM python:3.13-slim-bookworm

# 2. 从 uv 官方镜像中把 uv 二进制文件拷过来 (这是最优雅的安装方式)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. 设置环境变量
# 确保 uv 创建的虚拟环境在 PATH 里，这样直接敲 python 就是用虚拟环境里的
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
# 告诉 Playwright 浏览器装哪
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 4. 设置工作目录
WORKDIR /app

# 5. 安装系统基础依赖 (中文字体 + 必要的工具)
# 换源加速
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 6. 【关键】利用 uv 的缓存机制分层构建
# 先只复制配置文件，安装依赖。这样如果代码变了但依赖没变，Docker 会利用缓存跳过这一步
COPY pyproject.toml uv.lock ./

# 使用 uv sync 安装依赖
# --frozen: 严格按照 lock 文件安装，不更新版本
# --no-install-project: 只安装依赖，不安装当前项目本身(还没复制进来)
RUN uv sync --frozen --no-install-project

# 7. 安装 Playwright 的浏览器
# 注意：必须使用虚拟环境里的 playwright 命令
RUN playwright install chromium --with-deps

# 8. 复制剩下的业务代码
COPY . .

# 9. 再次同步，确保当前项目本身被安装 (如果有的话)
RUN uv sync --frozen

# 10.1. 如果代码里有 data 目录，先删掉
# 10.2. 创建一个软链接，把 /app/data 指向 /tmp
# 这样，你的代码以为它在往 ./data 写文件，实际上全写进了 /tmp
RUN rm -rf /app/data && ln -s /tmp /app/data

# 11. 启动命令
# 腾讯云 SCF 默认监听 9000 端口
# 假设你的入口文件是 bot.py
CMD ["python", "bot.py"]
