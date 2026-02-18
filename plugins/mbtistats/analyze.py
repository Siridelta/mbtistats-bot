from operator import xor
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional

# --- 正则定义 ---
# 1. 通用 MBTI 4字母代码 (全大写/全小写，支持模糊 X)
# 例如: INTP, esfp, ixxj, XNXX
MBTI_LOWER_REGEX = re.compile(r"(?:(?P<EI>[eix])(?P<SN>[nsx])(?P<TF>[tfx])(?P<JP>[pjx]))")
MBTI_UPPER_REGEX = re.compile(r"(?:(?P<EI>[EIX])(?P<SN>[NSX])(?P<TF>[TFX])(?P<JP>[PJX]))")

# 2. OPS 类型正则 (仅匹配其中的两主功能部分)
# 例如: FF-Ti/Ne-CP/B(S) 中的 Ti/Ne 或 Ne/Ti
OPS_DO_REGEX = re.compile(r"(?:(?P<D_TF>[TF])(?P<D_ei>[ie])/(?P<O_SN>[NS])(?P<O_ei>[ie]))")
OPS_OD_REGEX = re.compile(r"(?:(?P<O_SN>[NS])(?P<O_ei>[ie])/(?P<D_TF>[TF])(?P<D_ei>[ie]))")


def parse_mbti_from_text(text: str) -> Optional[Dict[str, Dict[str, bool]]]:
    """
    从文本中解析 MBTI 类型。
    优先匹配标准 4 字母代码，其次尝试 OPS 代码。
    返回格式为 MBTI 识别数据，集合用户声明的所有可能性，并反映成4维度上的单取值/双取值（模糊取值）。
    MBTI 识别数据格式：
    {
        "EI": { "E": True, "I": False },
        "SN": { "S": True, "N": False },
        "TF": { "T": True, "F": False },
        "JP": { "J": True, "P": False },
    }
    如果未找到则返回 None。
    """
    if not text:
        return None
    
    mbti_data = {
        "EI": { "E": False, "I": False },
        "SN": { "S": False, "N": False },
        "TF": { "T": False, "F": False },
        "JP": { "J": False, "P": False },
    }
    
    # 1. 尝试匹配标准 4 字母
    
    def handle_common_match(match: re.Match) -> None:
        match match.group("EI").upper():
            case "E":
                mbti_data["EI"]["E"] = True
            case "I":
                mbti_data["EI"]["I"] = True
            case "X":
                mbti_data["EI"]["E"] = True
                mbti_data["EI"]["I"] = True
            case _:
                raise Exception("Internal Error: Unexpcted Regex Match Result")
        match match.group("SN").upper():
            case "S":
                mbti_data["SN"]["S"] = True
            case "N":
                mbti_data["SN"]["N"] = True
            case "X":
                mbti_data["SN"]["S"] = True
                mbti_data["SN"]["N"] = True
            case _:
                raise Exception("Internal Error: Unexpcted Regex Match Result")
        match match.group("TF").upper():
            case "T":
                mbti_data["TF"]["T"] = True
            case "F":
                mbti_data["TF"]["F"] = True
            case "X":
                mbti_data["TF"]["T"] = True
                mbti_data["TF"]["F"] = True
            case _:
                raise Exception("Internal Error: Unexpcted Regex Match Result")
        match match.group("JP").upper():
            case "J":
                mbti_data["JP"]["J"] = True
            case "P":
                mbti_data["JP"]["P"] = True
            case "X":
                mbti_data["JP"]["J"] = True
                mbti_data["JP"]["P"] = True
            case _:
                raise Exception("Internal Error: Unexpcted Regex Match Result")

    for match in MBTI_LOWER_REGEX.finditer(text):
        handle_common_match(match)
    for match in MBTI_UPPER_REGEX.finditer(text):
        handle_common_match(match)
    
    # 2. 尝试匹配 OPS

    def handle_ops_match(match: re.Match, is_ops_DO: bool) -> None:
        D_TF = match.group("D_TF")
        D_ei = match.group("D_ei")
        O_SN = match.group("O_SN")
        O_ei = match.group("O_ei")
        if not (D_TF and D_ei and O_SN and O_ei):
            raise Exception("Internal Error: Unexpcted Regex Match Result")
        
        if is_ops_DO:   # Dx/Ox 类型

            if D_TF == "T":
                mbti_data["TF"]["T"] = True
            elif D_TF == "F":
                mbti_data["TF"]["F"] = True
            else:
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            
            if D_ei == "e":
                mbti_data["EI"]["E"] = True
                mbti_data["JP"]["J"] = True
            elif D_ei == "i":
                mbti_data["EI"]["I"] = True
                mbti_data["JP"]["P"] = True
            else:   
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            
            if not (O_SN == "S" or O_SN == "N"):
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            if not (O_ei == "e" or O_ei == "i"):
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            # De/Oe 型, Di/Oi 型下 mbti 式的 NS 标记与 OPS 的 Ox 标记相反；De/Oi 型, Di/Oe 型下 mbti 式的 NS 标记与 OPS 的 Dx 标记相同。
            invert_NS = (D_ei == "e" and O_ei == "e") or (D_ei == "i" and O_ei == "i")
            if xor(O_SN == "S", invert_NS):
                mbti_data["SN"]["S"] = True
            else:
                mbti_data["SN"]["N"] = True
        
        else:   # Ox/Dx 类型
            if O_SN == "S":
                mbti_data["SN"]["S"] = True
            elif O_SN == "N":
                mbti_data["SN"]["N"] = True
            else:
                raise Exception("Internal Error: Unexpcted Regex Match Result")

            if O_ei == "e":
                mbti_data["EI"]["E"] = True
                mbti_data["JP"]["P"] = True
            elif O_ei == "i":
                mbti_data["EI"]["I"] = True
                mbti_data["JP"]["J"] = True
            else:
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            
            if not (D_TF == "T" or D_TF == "F"):
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            if not (D_ei == "e" or D_ei == "i"):
                raise Exception("Internal Error: Unexpcted Regex Match Result")
            # Oe/De 型, Oi/Di 型下 mbti 式的 TF 标记与 OPS 的 Ox 标记相反；Oe/Di 型, Oi/De 型下 mbti 式的 TF 标记与 OPS 的 Dx 标记相同。
            invert_TF = (O_ei == "e" and D_ei == "e") or (O_ei == "i" and D_ei == "i")
            if xor(D_TF == "T", invert_TF):
                mbti_data["TF"]["T"] = True
            else:
                mbti_data["TF"]["F"] = True

    for match in OPS_DO_REGEX.finditer(text):
        handle_ops_match(match, is_ops_DO=True)
    for match in OPS_OD_REGEX.finditer(text):
        handle_ops_match(match, is_ops_DO=False)
    
    # 3. 判断有有效结果的标准：各特质维度都至少有一个为 True
    for trait_dim in mbti_data.keys():
        if not any(mbti_data[trait_dim].values()):
            return None

    return mbti_data

def analyze_type_stats(member_names: List[str]) -> Tuple[List[Dict], int]:
    """
    统计 MBTI 16 类型分布
    
    Args:
        member_names: 成员昵称列表
        
    Returns:
        Tuple[List[Dict], int]: (ECharts 数据列表, 有效样本总数)
        数据列表格式: [
            {
                "name": "INTP",
                "value": 15,
            },
            ...
            {
                "name": "模糊类型",
                "value": 10,
            }
        ]
    """

    mbti_type_countsource = []
    
    def parse_name_from_mbti(mbti_data: Dict[str, Dict[str, bool]]) -> str:
        name = ""
        for trait_dim in ["EI", "SN", "TF", "JP"]:  # 维度枚举, 按照正确顺序
            valid_traits = [trait for trait, isValid in mbti_data[trait_dim].items() if isValid]
            if len(valid_traits) == 0:
                raise Exception("Internal Error: Unexpcted MBTI Data")
            elif len(valid_traits) == 1:
                name += valid_traits[0]
            elif len(valid_traits) == 2:
                name = 'fuzzy-type'
                break
            else:
                raise Exception("Internal Error: Unexpcted MBTI Data")
        return name
    
    for name in member_names:
        mbti = parse_mbti_from_text(name)
        if not mbti:
            continue
        mbti_type_countsource.append(parse_name_from_mbti(mbti))
            
    total_count = len(mbti_type_countsource)
    counts = Counter(mbti_type_countsource)
    
    # 转换为 ECharts 格式
    # 须确保数据顺序，确保数据稳定性，顺序不稳定会导致等价性检验失效
    expected_names = ['INTP', 'INTJ', 'ENTP', 'ENTJ', 'INFP', 'INFJ', 'ENFP', 'ENFJ', 'ISTP', 'ISTJ', 'ESTP', 'ESTJ', 'ISFP', 'ISFJ', 'ESFP', 'ESFJ', 'fuzzy-type']
    chart_data = [{ "name": name, "value": 0 } for name in expected_names]
    for name, value in counts.items():
        chart_data[expected_names.index(name)]["value"] = value
        if name == 'fuzzy-type':
            chart_data[expected_names.index(name)]["name"] = '模糊类型'
    
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
    result = {
        "EI": {"E": 0, "I": 0, "X": 0},
        "SN": {"S": 0, "N": 0, "X": 0},
        "TF": {"T": 0, "F": 0, "X": 0},
        "JP": {"J": 0, "P": 0, "X": 0}
    }
    
    valid_count = 0
    
    for name in member_names:
        mbti = parse_mbti_from_text(name)
        if not mbti:
            continue
            
        valid_count += 1

        # 维度 1: E/I/X
        result["EI"]["E"] += 1 if mbti["EI"]["E"] and not mbti["EI"]["I"] else 0
        result["EI"]["I"] += 1 if mbti["EI"]["I"] and not mbti["EI"]["E"] else 0
        result["EI"]["X"] += 1 if mbti["EI"]["E"] and mbti["EI"]["I"] else 0
        # 维度 2: S/N/X
        result["SN"]["S"] += 1 if mbti["SN"]["S"] and not mbti["SN"]["N"] else 0
        result["SN"]["N"] += 1 if mbti["SN"]["N"] and not mbti["SN"]["S"] else 0
        result["SN"]["X"] += 1 if mbti["SN"]["S"] and mbti["SN"]["N"] else 0
        # 维度 3: T/F/X
        result["TF"]["T"] += 1 if mbti["TF"]["T"] and not mbti["TF"]["F"] else 0
        result["TF"]["F"] += 1 if mbti["TF"]["F"] and not mbti["TF"]["T"] else 0
        result["TF"]["X"] += 1 if mbti["TF"]["T"] and mbti["TF"]["F"] else 0
        # 维度 4: J/P/X
        result["JP"]["J"] += 1 if mbti["JP"]["J"] and not mbti["JP"]["P"] else 0
        result["JP"]["P"] += 1 if mbti["JP"]["P"] and not mbti["JP"]["J"] else 0
        result["JP"]["X"] += 1 if mbti["JP"]["J"] and mbti["JP"]["P"] else 0
    
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
