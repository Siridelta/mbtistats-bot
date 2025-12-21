import argparse
import time
import json
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# 配置
TEMPLATE_DIR_NAME = "template"
MOCK_FILE_NAME = "mock.json"
INDEX_FILE_NAME = "index.html"
PREVIEW_FILE_NAME = "preview.html"

# 设置环境
root_dir = Path(__file__).parent
template_base_dir = root_dir / TEMPLATE_DIR_NAME
env = Environment(loader=FileSystemLoader(template_base_dir))

def get_available_modes():
    """扫描 template 目录，返回所有包含 index.html 的子目录名"""
    modes = []
    if not template_base_dir.exists():
        return modes
    
    for path in template_base_dir.iterdir():
        if path.is_dir() and (path / INDEX_FILE_NAME).exists():
            modes.append(path.name)
    return modes

def render_preview(mode):
    """渲染指定模式的页面"""
    mode_dir = template_base_dir / mode
    template_path = f"{mode}/{INDEX_FILE_NAME}"
    mock_path = mode_dir / MOCK_FILE_NAME
    output_path = mode_dir / PREVIEW_FILE_NAME

    # 1. 加载 Mock 数据
    data = {}
    if not mock_path.exists():
        print(f"❌ 未找到 Mock 数据文件: {MOCK_FILE_NAME}")
        return False
    try:
        with open(mock_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Mock 数据格式错误 ({MOCK_FILE_NAME}): {e}")
        return False
    except Exception as e:
        print(f"❌ 读取 Mock 数据失败: {e}")
        return False

    # 2. 加载模板
    try:
        template = env.get_template(template_path)
    except Exception as e:
        print(f"❌ 找不到模板文件 ({template_path}): {e}")
        return False

    # 3. 渲染 HTML
    try:
        html_content = template.render(**data)
    except Exception as e:
        print(f"❌ Jinja2 渲染出错: {e}")
        return False
    
    # 4. 输出文件
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"❌ 写入预览文件失败: {e}")
        return False
    
    print(f"✅ [{mode}] 预览已更新: {output_path}")
    return True

def watch_mode(mode):
    """监听文件变化并自动重绘"""
    mode_dir = template_base_dir / mode
    if not mode_dir.exists():
        print(f"❌ 目录不存在: {mode_dir}")
        return

    print(f"🚀 启动调试模式: {mode}")
    print(f"📂 监听目录: {mode_dir}")
    print(f"   - {INDEX_FILE_NAME}")
    print(f"   - {MOCK_FILE_NAME}")
    print(f"💡 请确保已启动 Live Server 监听 {mode}/{PREVIEW_FILE_NAME}")

    # 初始渲染
    render_preview(mode)

    # 需要观察的文件列表
    files_to_watch = {
        "index": mode_dir / INDEX_FILE_NAME,
        "mock": mode_dir / MOCK_FILE_NAME
    }
    
    # 存在状态
    last_exists = {
        "index": None,
        "mock": None
    }
    # 最后修改时间
    last_mtimes = {
        "index": None,
        "mock": None
    }

    try:
        while True:
            needs_render = False
            
            for key, file_path in files_to_watch.items():      
                detected_change = False          
                try:
                    # 存在状态
                    current_exist = file_path.exists()
                    last_exist = last_exists.get(key)

                    if last_exist is None:
                        last_exists[key] = current_exist
                        last_exist = current_exist

                    # 最后修改时间
                    current_mtime = file_path.stat().st_mtime
                    last_mtime = last_mtimes.get(key)

                    if last_mtime is None:
                        last_mtimes[key] = current_mtime
                        last_mtime = current_mtime

                    # 对比检查
                    if last_exist != current_exist:
                        last_exists[key] = current_exist
                        detected_change = True
                
                    if current_mtime != last_mtime:
                        last_mtimes[key] = current_mtime
                        detected_change = True
                    
                    if detected_change:
                        print(f"⚡ 检测到 {file_path.name} 变化...")
                        needs_render = True
                    
                except OSError:
                    pass
            
            if needs_render:
                render_preview(mode)
                
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n🛑 已停止监听")

if __name__ == "__main__":
    available_modes = get_available_modes()
    
    parser = argparse.ArgumentParser(description="前端页面开发调试工具")
    parser.add_argument(
        "mode", nargs="?", 
        help=f"页面模式 (template/ 模板目录下的子目录名，目前检测到可用模式: {', '.join(available_modes)})"
    )
    
    args = parser.parse_args()
    
    target_mode = args.mode

    # 如果没有指定 mode，或者指定的 mode 不存在
    if not target_mode:
        if not available_modes:
            print("❌ 在 template/ 目录下未找到任何包含 index.html 的子目录，没有可用模式")
            sys.exit(1)
        # 默认选择第一个，或者这里可以改为让用户选择
        if "mbti-stats" in available_modes:
            target_mode = "mbti-stats"
        else:
            target_mode = available_modes[0]
        print(f"ℹ️ 未指定模式，自动选择: {target_mode}")
    elif target_mode not in available_modes:
        print(f"❌ 模式 '{target_mode}' 不存在 (找不到 {target_mode}/index.html)")
        print(f"可用模式: {', '.join(available_modes)}")
        sys.exit(1)

    watch_mode(target_mode)
