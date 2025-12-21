import argparse
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# --- 1. 准备模拟数据 ---

# 旧版数据
def get_mock_data_type():
    data = [
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
    data.sort(key=lambda x: x['value'], reverse=True)
    return {
        "title": "MBTI 类型分布统计 (开发预览)",
        "group_name": "前端调试测试群",
        "total_count": sum(item['value'] for item in data),
        "data": data
    }

def get_mock_data_trait():
    # 模拟特质统计数据
    # 格式参考：E/I, S/N, T/F, J/P 的分布
    return {
        "title": "MBTI 特质分布统计 (开发预览)",
        "group_name": "前端调试测试群",
        "total_count": 172, # 示例总数
        "data": {
            "EI": {"E": 10, "I": 20, "X": 0},
            "SN": {"S": 15, "N": 15, "X": 1},
            "TF": {"T": 12, "F": 18, "X": 0},
            "JP": {"J": 14, "P": 16, "X": 1}
        }
    }

# 新版合一数据
def get_mock_data_mbti():
    return {
        "title": "MBTI 类型与特质分布统计 (开发预览)",
        "group_name": "前端调试测试群",
        "total_count": 213,
        "type_data": get_mock_data_type(),
        "trait_data": get_mock_data_trait(),
        "type_history_data": [],
        "trait_history_data": []
    }

# --- 2. 配置 ---
CONFIG = {
    "type-stats": {
        "template_subpath": "type-stats/index.html",
        "output_subpath": "type-stats/preview.html",
        "data_provider": get_mock_data_type
    },
    "trait-stats": {
        "template_subpath": "trait-stats/index.html",
        "output_subpath": "trait-stats/preview.html",
        "data_provider": get_mock_data_trait
    },
    "mbti-stats": {
        "template_subpath": "mbti-stats/index.html",
        "output_subpath": "mbti-stats/preview.html",
        "data_provider": get_mock_data_mbti
    }
}

# --- 3. 渲染逻辑 ---
root_dir = Path(__file__).parent
template_base_dir = root_dir / "template"
env = Environment(loader=FileSystemLoader(template_base_dir))

def render_preview(mode):
    cfg = CONFIG[mode]
    template_path = cfg["template_subpath"]
    
    # 加载模板
    try:
        # Jinja2 loader is relative to template_base_dir
        # Since template_subpath is like "type-stats/index.html", it should work if file exists
        template = env.get_template(template_path)
    except Exception as e:
        print(f"❌ 找不到模板文件 ({template_path}): {e}")
        return None

    # 获取数据
    data = cfg["data_provider"]()
    
    # 渲染 HTML
    try:
        html_content = template.render(**data)
    except Exception as e:
        print(f"❌ 渲染出错: {e}")
        return None
    
    # 输出文件
    output_path = template_base_dir / cfg["output_subpath"]
    # 确保父目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ [{mode}] 预览文件已生成: {output_path}")
    return output_path

def watch_mode(mode):
    cfg = CONFIG[mode]
    # template_path is relative to template_base_dir
    # We need absolute path for watching
    target_file = template_base_dir / cfg["template_subpath"]
    
    print(f"🚀 启动模式: {mode}")
    print(f"👀 正在监听 {target_file} 的变化...")
    print(f"💡 请确保已启动 Live Server 监听 {cfg['output_subpath']}")
    
    last_mtime = 0
    
    try:
        while True:
            try:
                # 检查文件是否存在
                if not target_file.exists():
                    # 如果是首次运行或者文件刚被删除，提示一下，然后等待
                    if last_mtime != -1: 
                        print(f"⚠️ 目标文件不存在: {target_file}，等待创建...")
                        last_mtime = -1
                    time.sleep(1)
                    continue

                # 获取文件修改时间
                current_mtime = target_file.stat().st_mtime
                
                # 如果时间戳改变
                if current_mtime != last_mtime:
                    if last_mtime != 0 and last_mtime != -1: # 非首次运行才提示
                        print("⚡ 检测到文件变化，正在重新渲染...")
                    
                    render_preview(mode)
                    last_mtime = current_mtime
                    
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ 发生错误: {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 已停止监听")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="前端模板开发调试工具")
    parser.add_argument("mode", nargs="?", default="type-stats", choices=CONFIG.keys(), help="调试模式 (默认: type-stats)")
    
    args = parser.parse_args()
    watch_mode(args.mode)
