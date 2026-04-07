"""
分句服务：将原文拆分为句子列表。
MVP 使用正则启发式分句（适合英文/中文混合）；后续可替换为 spaCy 等。
"""
import re
from typing import List


_SPLIT_RE = re.compile(
    r'(?<=[。！？!?\.…])\s*'   # 中英文句末标点后
    r'|(?<=\n)',                # 或换行符后
)

_MIN_LEN = 2      # 忽略空/极短片段
_MAX_LEN = 1000   # 超长句截断阈值（字符）


def split_text(text: str, max_chars: int = _MAX_LEN) -> List[str]:
    """
    将文本拆分为句子列表，过滤空句、过长句截断提示。
    返回值中每个元素都是非空字符串。
    """
    raw = _SPLIT_RE.split(text.strip())
    sentences: List[str] = []
    for s in raw:
        s = s.strip()
        if len(s) < _MIN_LEN:
            continue
        if len(s) > max_chars:
            # 超长句：按 max_chars 硬切，每段加省略标记
            for i in range(0, len(s), max_chars):
                chunk = s[i: i + max_chars].strip()
                if chunk:
                    sentences.append(chunk)
        else:
            sentences.append(s)
    return sentences
