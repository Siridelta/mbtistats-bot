from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# --- 1. 准备模拟数据 (和 Bot 里的逻辑一致) ---
mock_data = [
    {"name": "INTP", "value": 15}, {"name": "INTJ", "value": 8},
    {"name": "ENTP", "value": 12}, {"name": "ENTJ", "value": 5},
    {"name": "INFP", "value": 20}, {"name": "INFJ", "value": 10},
    {"name": "ENFP", "value": 18}, {"name": "ENFJ", "value": 7},
    {"name": "ISTP", "value": 6},  {"name": "ISTJ", "value": 9},
    {"name": "ESTP", "value": 4},  {"name": "ESTJ", "value": 11},
    {"name": "ISFP", "value": 5},  {"name": "ISFJ", "value": 14},
    {"name": "ESFP", "value": 8},  {"name": "ESFJ", "value": 12},
    {"name": "模糊类型", "value": 10}
]
# 按 value 从大到小排序
mock_data.sort(key=lambda x: x['value'], reverse=True)

# --- 2. 设置 Jinja2 环境 ---
root_dir = Path(__file__).parent
template_dir = root_dir / "template"
env = Environment(loader=FileSystemLoader(template_dir))

def render_preview():
    # 加载模板
    try:
        template = env.get_template("chart.html")
    except Exception as e:
        print(f"❌ 找不到模板文件: {e}")
        return None

    # 渲染 HTML
    html_content = template.render(
        title="MBTI 类型分布统计 (开发预览)",
        group_name="前端调试测试群",
        total_count=sum(item['value'] for item in mock_data),
        data=mock_data
    )
    
    # --- 3. 输出为纯 HTML 文件 ---
    # 我们把它输出为 preview.html，这样浏览器就能直接看了
    output_path = template_dir / "preview.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ 预览文件已生成: {output_path}")
    return output_path

def watch_mode():
    import time
    target_file = template_dir / "chart.html"
    print(f"👀 正在监听 {target_file} 的变化...")
    print("💡 请确保已启动 Live Server 监听 template/preview.html")
    
    last_mtime = 0
    
    try:
        while True:
            try:
                # 获取文件修改时间
                current_mtime = target_file.stat().st_mtime
                
                # 如果时间戳改变
                if current_mtime != last_mtime:
                    if last_mtime != 0: # 非首次运行才提示
                        print("⚡ 检测到文件变化，正在重新渲染...")
                    
                    render_preview()
                    last_mtime = current_mtime
                    
                time.sleep(0.5)
            except FileNotFoundError:
                print("⚠️ 目标文件不存在，等待恢复...")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 已停止监听")

if __name__ == "__main__":
    watch_mode()
