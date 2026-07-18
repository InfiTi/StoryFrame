"""商品信息 Markdown 解析器

从带货商品信息 Markdown 文件中提取产品特征，
重点提取对「图生视频」提示词有用的物理质感关键词。
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductInfo:
    """从商品信息提取的结构化产品数据"""
    name: str = ""                          # 产品名称
    title: str = ""                         # 原始标题
    category: str = ""                      # 商品类目（饼干/面包/牛肉干等）
    price: str = ""                         # 到手价
    sold: str = ""                          # 已售数量
    rating: str = ""                        # 好评率
    trend_rank: str = ""                    # 趋势榜排名
    shop: str = ""                          # 店铺
    specs: List[str] = field(default_factory=list)  # 规格列表
    description: str = ""                   # 产品描述（组合）
    selling_points: List[str] = field(default_factory=list)  # 卖点列表
    texture_keywords: List[str] = field(default_factory=list)  # 质感关键词
    flavor_tags: List[str] = field(default_factory=list)       # 口味标签
    review_keywords: List[str] = field(default_factory=list)   # 评价关键词
    top_copies: List[str] = field(default_factory=list)        # 高转化文案
    raw_text: str = ""                      # 原始全文


# 质感关键词映射表：中文描述 → 英文视觉语言
TEXTURE_MAP = {
    "酥脆": ["crispy", "crunchy texture", "flaky layers", "shatter when broken"],
    "脆": ["crispy", "crunchy", "snapping texture"],
    "酥": ["flaky", "crumbly", "delicate layers"],
    "柔软": ["soft", "pillowy", "gentle deformation when touched"],
    "软": ["soft texture", "yielding", "tender"],
    "Q弹": ["bouncy", "elastic", "springy texture", "resilient"],
    "弹": ["bouncy", "springy", "elastic rebound"],
    "嚼劲": ["chewy", "resilient bite", "satisfying chew"],
    "糯": ["sticky", "glutinous", "soft and adhesive"],
    "滑": ["smooth", "silky surface", "glossy"],
    "嫩": ["tender", "soft and delicate"],
    "薄": ["thin", "delicate thickness", "translucent edge"],
    "厚": ["thick", "substantial", "hearty"],
    "香": ["aromatic", "rich aroma", "fragrant"],
    "咸香": ["savory", "rich savory aroma"],
    "咸": ["savory", "salty flavor"],
    "甜": ["sweet", "sweet glaze"],
    "辣": ["spicy", "red chili accent"],
    "鲜": ["umami", "fresh savoriness"],
    "掉渣": ["crumbly", "flaky crumbs falling", "shattering crust"],
    "一口惊艳": ["bite-sized appeal", "inviting cross-section"],
    "麦香": ["wheat aroma", "golden wheat color"],
    "肉松": ["meat floss", "fibrous fluffy filling", "pulled pork texture"],
    "牛肉": ["beef filling", "rich meat filling", "savory meat layer"],
    "夹心": ["filled center", "cross-section showing filling", "stuffed"],
    "独立包装": ["individually wrapped", "single-serve packaging"],
    "包装": ["packaging design", "product packaging"],
    "饼干": ["biscuit", "cookie", "cracker"],
    "轻盈": ["light", "airy texture", "weightless feel"],
    "浓郁": ["rich", "intense flavor", "deep coating"],
    "丝滑": ["silky smooth", "glossy surface", "velvety"],
    "颗粒感": ["granular texture", "crystal texture", "crystalline"],
    "流心": ["molten center", "flowing filling", "liquid core"],
    "层次": ["layered", "visible layers", "stratified texture"],
}


def scan_product_directory(directory: str) -> list[dict]:
    """扫描商品目录，返回包含 .md 文件的商品列表
    返回 [{name, md_path, folder}, ...]
    """
    result = []
    if not directory:
        return result
    base = Path(directory)
    if not base.exists():
        return result
    for item in sorted(base.iterdir()):
        if not item.is_dir():
            continue
        # 在子文件夹中找 .md 文件
        md_files = list(item.glob("*.md"))
        if not md_files:
            continue
        # 用文件夹名作为商品名
        result.append({
            "name": item.name,
            "md_path": str(md_files[0]),
            "folder": str(item),
        })
    return result


def parse_product_markdown(file_path: str) -> ProductInfo:
    """解析商品信息 Markdown 文件，提取产品特征"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    text = path.read_text(encoding="utf-8")
    info = ProductInfo(raw_text=text)

    # 1. 提取标题（第一行 # 开头）
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if title_match:
        info.title = title_match.group(1).strip()
        # 从标题中提取简化产品名
        # 去掉"独立包装""充饥解馋""网红""商超同款""美味零食"等修饰词
        name = info.title
        for word in ["独立包装", "充饥解馋", "网红", "商超同款", "美味零食",
                      "小零食", "零食", "同款"]:
            name = name.replace(word, "")
        info.name = name.strip(" -·")

    # 2. 提取基础信息表格
    table_pattern = r'\|\s*(\S+)\s*\|\s*(\S.*?)\s*\|'
    for match in re.finditer(table_pattern, text):
        key, val = match.group(1).strip(), match.group(2).strip()
        if key == "商品标题":
            if not info.title:
                info.title = val
        elif key == "商品类目":
            info.category = val
        elif key == "到手价":
            info.price = val
        elif key == "已售":
            info.sold = val
        elif key == "好评率":
            info.rating = val
        elif key == "趋势榜":
            info.trend_rank = val
        elif key == "店铺":
            info.shop = val

    # 3. 提取规格信息（从评价中提取）
    spec_pattern = r'规格:\^\s*(.+?)(?:\s+发布)'
    for match in re.finditer(spec_pattern, text):
        spec = match.group(1).strip()
        if spec and spec not in info.specs:
            info.specs.append(spec)

    # 4. 提取带货文案（表格中的文案列）
    copy_pattern = r'\|\s*\d{2}/\d{2}\s*\|.*?\|\s*(.+?)\s*\|'
    for match in re.finditer(copy_pattern, text):
        copy = match.group(1).strip()
        if copy and len(copy) > 5 and copy not in info.top_copies:
            # 清理 copy 中的 # 标签
            clean = re.sub(r'#\S+', '', copy).strip()
            if clean and len(clean) > 5:
                info.top_copies.append(clean)

    # 5. 提取好评标签
    review_section = ""
    if "好评标签" in text:
        start = text.index("好评标签")
        end = text.index("差评标签") if "差评标签" in text else len(text)
        review_section = text[start:end]

    # 提取标签括号里的内容
    tag_pattern = r'(\S+?)\s*[（(]\s*\d+\s*[）)]'
    for match in re.finditer(tag_pattern, review_section):
        tag = match.group(1).strip()
        if tag and tag not in info.review_keywords:
            info.review_keywords.append(tag)

    # 6. 提取评价摘录
    review_text = ""
    if "评价摘录" in text:
        start = text.index("评价摘录")
        review_text = text[start:]

    # 7. 从全文 + 文案 + 评价中提取质感关键词
    search_text = text
    for keyword in TEXTURE_MAP:
        if keyword in search_text:
            if keyword not in info.texture_keywords:
                info.texture_keywords.append(keyword)

    # 7.1 提取口味标签
    flavor_pattern = re.compile(r'(\b|(?<=[，。、\s]))(酸甜?|微酸|酸|微甜|甜|微辣|辣|中辣|重辣|咸香?|咸|鲜|微苦|苦|酸甜可口|香|咸甜|香辣|麻辣|五香味|奶香|奶|巧克力味|抹茶味|蜂蜜味|果汁味|水果味|麦香|奶香?味?|咸蛋黄味|芝士味|奶油味)(\b|(?=[，。、\s]))')
    for m in flavor_pattern.finditer(text):
        tag = m.group(1).strip()
        if tag and tag not in info.flavor_tags:
            info.flavor_tags.append(tag)
    # 也从质感关键词中补充口味类词
    flavor_from_texture = ['香', '咸香', '咸', '甜', '辣', '鲜', '麦香', '浓郁']
    for kw in info.texture_keywords:
        if kw in flavor_from_texture and kw not in info.flavor_tags:
            info.flavor_tags.append(kw)
    # 从评价关键词中补充
    for kw in info.review_keywords:
        for ft in flavor_from_texture:
            if ft in kw and ft not in info.flavor_tags:
                info.flavor_tags.append(ft)

    # 7.5 提取商品类目（表格已有则直接用，没有则从趋势榜/标题 fallback）
    if not info.category:
        if info.trend_rank:
            if "饼干" in info.trend_rank:
                info.category = "饼干"
            elif "面包" in info.trend_rank:
                info.category = "面包"
            elif "牛肉干" in info.trend_rank:
                info.category = "牛肉干"
            elif "糕点" in info.trend_rank:
                info.category = "糕点"
            elif "坚果" in info.trend_rank:
                info.category = "坚果"
            elif "果干" in info.trend_rank:
                info.category = "果干"
            elif "糖果" in info.trend_rank:
                info.category = "糖果"
            elif "巧克力" in info.trend_rank:
                info.category = "巧克力"
            elif "膨化" in info.trend_rank:
                info.category = "膨化食品"
        if not info.category:
            title_text = info.title or ""
            if "饼干" in title_text or "曲奇" in title_text:
                info.category = "饼干"
            elif "面包" in title_text:
                info.category = "面包"
            elif "牛肉干" in title_text or "牛肉粒" in title_text:
                info.category = "牛肉干"
            elif "糕" in title_text or "蛋糕" in title_text:
                info.category = "糕点"
            elif "坚果" in title_text or "夏威夷果" in title_text or "腰果" in title_text:
                info.category = "坚果"
            elif "果干" in title_text or "芒果干" in title_text or "葡萄干" in title_text:
                info.category = "果干"
            elif "糖" in title_text:
                info.category = "糖果"
            elif "巧克力" in title_text:
                info.category = "巧克力"
            elif "薯片" in title_text or "锅巴" in title_text:
                info.category = "膨化食品"

    # 8. 组合产品描述
    desc_parts = []
    # 从标题提取核心品类
    if "饼干" in info.title:
        desc_parts.append("饼干/biscuit")
    elif "糕" in info.title:
        desc_parts.append("糕点/cake")
    elif "糖" in info.title:
        desc_parts.append("糖果/candy")

    # 从质感关键词提取特征
    if info.texture_keywords:
        desc_parts.append("、".join(info.texture_keywords[:8]))

    # 从规格提取包装信息
    if info.specs:
        # 取第一个规格的关键信息
        first_spec = info.specs[0]
        if "盒" in first_spec:
            desc_parts.append("盒装")
        if "包" in first_spec:
            desc_parts.append("独立小包装")

    info.description = "，".join(desc_parts)

    # 9. 组合卖点
    points = []
    # 从质感关键词取前5个作为卖点
    for kw in info.texture_keywords[:5]:
        points.append(kw)
    # 加上销量和价格信息
    if info.sold:
        points.append(f"已售{info.sold}")
    if info.price:
        points.append(f"到手价{info.price}")
    if info.trend_rank:
        points.append(info.trend_rank)

    info.selling_points = points

    return info


def texture_keywords_to_english(keywords: List[str]) -> List[str]:
    """将中文质感关键词转换为英文视觉描述"""
    result = []
    for kw in keywords:
        if kw in TEXTURE_MAP:
            result.extend(TEXTURE_MAP[kw])
    # 去重保序
    seen = set()
    unique = []
    for item in result:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def build_texture_description(info: ProductInfo) -> str:
    """将产品质感关键词组合成连贯的英文视觉描述"""
    en_keywords = texture_keywords_to_english(info.texture_keywords)
    if not en_keywords:
        return ""
    # 分层组织：材质 → 质感 → 动态
    return ", ".join(en_keywords)


def update_product_markdown(md_path: str, field: str, new_value: str) -> bool:
    """更新商品 Markdown 文件中表格的某个字段
    
    Args:
        md_path: Markdown 文件路径
        field: 字段名（如 "商品类目"）
        new_value: 新值
    
    Returns:
        True 如果成功更新（或新增）了字段
    """
    path = Path(md_path)
    if not path.exists():
        return False
    
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    
    # 在「商品基础信息」表格中查找并更新字段
    # 表格格式: | 字段 | 值 |
    pattern = re.compile(r'\|\s*' + re.escape(field) + r'\s*\|\s*(.+?)\s*\|')
    
    found = False
    updated = False
    in_table = False
    table_end = -1
    
    for i, line in enumerate(lines):
        # 检测表格开始
        if '商品基础信息' in line:
            in_table = True
            continue
        if in_table:
            # 表格结束标志：空行或下一个 ## 标题
            if line.strip() == '' or line.startswith('## '):
                table_end = i
                break
            # 检测分隔线 |---|---|
            if re.match(r'\|[-\s|]+\|', line):
                continue
            match = pattern.search(line)
            if match:
                # 替换该行的值
                lines[i] = f'| {field} | {new_value} |'
                updated = True
                found = True
    
    if not found and table_end >= 0:
        # 字段不存在，在表格末尾插入新行
        lines.insert(table_end, f'| {field} | {new_value} |')
        updated = True
    
    if updated:
        path.write_text("\n".join(lines), encoding="utf-8")
    return updated
