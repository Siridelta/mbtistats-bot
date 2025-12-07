import re
from collections import Counter
from typing import List, Dict, Tuple, Optional

# --- 正则定义 ---
# 1. 通用 MBTI 4字母代码 (全大写/全小写，支持模糊 X)
# 例如: INTP, esfp, ixxj, XNXX
MBTI_REGEX = re.compile(r"([eix][nsx][tfx][pjx])", )

# 2. OPS 类型正则 (仅匹配其中的两主功能部分)
# 例如: FF-Ti/Ne-CP/B(S) 中的 Ti/Ne 或 Ne/Ti
# OPS 实际上比较复杂，这里先按简易逻辑：匹配 [TF][ie]/[NS][ie] 或 [NS][ie]/[TF][ie]
OPS_REGEX = re.compile(r"([tf][ie]/[ns][ie]|[ns][ie]/[tf][ie])", re.IGNORECASE)

def parse_mbti_from_text(text: str) -> Optional[str]:
    """
    从文本中解析 MBTI 类型。
    优先匹配标准 4 字母代码，其次尝试 OPS 代码。
    返回大写的类型字符串 (如 "INTP")，如果未找到则返回 None。
    """
    if not text:
        return None
        
    # 1. 尝试匹配标准 4 字母
    match = MBTI_REGEX.search(text)
    if match:
        return match.group(1).upper()
    
    # 2. 尝试匹配 OPS
    match_ops = OPS_REGEX.search(text)
    if match_ops:
        # 返回匹配到的主功能对，例如 "Ti/Ne"
        # 统一转为首字母大写格式 (例如 Ti/Ne)
        raw = match_ops.group(1)
        # 简单的格式化：全部大写或者保持原样? OPS 通常是 Ti/Ne 大小写混合
        # 这里为了图表美观，暂时保持原样但确保首字母大写
        return raw  
    
    return None

def analyze_type_stats(member_names: List[str]) -> Tuple[List[Dict], int]:
    """
    统计 MBTI 16 类型分布
    
    Args:
        member_names: 成员昵称列表
        
    Returns:
        Tuple[List[Dict], int]: (ECharts 数据列表, 有效样本总数)
        数据列表格式: [{"name": "INTP", "value": 15}, ...]
    """
    mbti_data = []
    for name in member_names:
        mbti = parse_mbti_from_text(name)
        if mbti:
            mbti_data.append(mbti)
            
    total_count = len(mbti_data)
    counts = Counter(mbti_data)
    
    # 转换为 ECharts 格式
    chart_data = [{"name": k, "value": v} for k, v in counts.items()]
    # 按数量降序排序
    chart_data.sort(key=lambda x: x['value'], reverse=True)
    
    return chart_data, total_count

def analyze_trait_stats(member_names: List[str]) -> Tuple[Dict[str, Dict[str, int]], int]:
    """
    统计 MBTI 4 维度特质分布 (E/I, S/N, T/F, J/P)
    
    Args:
        member_names: 成员昵称列表
        
    Returns:
        Tuple[Dict[str, Dict[str, int]], int]: (特质分布数据, 有效样本总数)
        数据格式: {
            "EI": {"E": 10, "I": 20, "X": 1},
            "SN": {"S": 15, "N": 15, "X": 1},
            "TF": {"T": 12, "F": 18, "X": 1},
            "JP": {"J": 14, "P": 16, "X": 1}
        }
    """
    traits = {
        "EI": Counter(),
        "SN": Counter(),
        "TF": Counter(),
        "JP": Counter()
    }
    
    valid_count = 0
    
    for name in member_names:
        mbti = parse_mbti_from_text(name)
        if not mbti:
            continue
            
        valid_count += 1
        
        # mbti 字符串例如 "INTP" 或 "IXTP"
        # 维度 1: E/I/X
        e_i = mbti[0]
        traits["EI"][e_i] += 1
        
        # 维度 2: S/N/X
        s_n = mbti[1]
        traits["SN"][s_n] += 1
        
        # 维度 3: T/F/X
        t_f = mbti[2]
        traits["TF"][t_f] += 1
        
        # 维度 4: J/P/X
        j_p = mbti[3]
        traits["JP"][j_p] += 1
        
    # 转换为普通字典返回
    result = {k: dict(v) for k, v in traits.items()}
    return result, valid_count

def get_mock_data() -> Tuple[List[Dict], int]:
    """
    返回演示用的 Mock 数据 (类型统计)
    """
    mbti_counts = Counter({
        "INTP": 15, "INTJ": 8, "ENTP": 12, "ENTJ": 5,
        "INFP": 20, "INFJ": 10, "ENFP": 18, "ENFJ": 7,
        "ISTP": 6,  "ISTJ": 9, "ESTP": 4,  "ESTJ": 11,
        "ISFP": 5,  "ISFJ": 14, "ESFP": 8,  "ESFJ": 12
    })
    chart_data = [{"name": k, "value": v} for k, v in mbti_counts.items()]
    chart_data.sort(key=lambda x: x['value'], reverse=True)
    return chart_data, 164

def get_mock_trait_data() -> Tuple[Dict[str, Dict[str, int]], int]:
    """
    返回演示用的 Mock 数据 (特质统计)
    """
    # 基于上面的 Mock 数据粗略计算
    # 总数 164
    return {
        "EI": {"E": 77, "I": 87},
        "SN": {"S": 69, "N": 95},
        "TF": {"T": 60, "F": 104}, # 修正计算
        "JP": {"J": 76, "P": 88}
    }, 164
