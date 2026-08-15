"""知识库与检索：JSON 存储的 FAQ 条目 + BM25 全文检索（jieba 中文分词）。

技术选型说明（面试可讲）：
- 知识库规模在百级条目时，BM25 的检索质量与可解释性都足够，且零外部依赖、零向量库成本；
- 每个条目带 category/tags，检索结果可以被 Agent 引用（如 kb-012），让“建议答复”有据可查；
- 若知识库增长到万级，可平滑替换为向量检索（embedding + 余弦相似度），接口不变。
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import jieba

import config

# 停用词（简化版：标点 + 常见无实义词）
_STOPWORDS = set("的了和是在有就都而及与或一个我们你们他们这那我你他她它很更最不也还又才只没被把让向到于为从"
                 "什么怎么如何为什么可以可能应该需要已经进行通过对于关于根据按照以及并且或者如果因为所以但是"
                 "：；，。！？、（）【】《》“”‘’…—\n\t ")

# BM25 经验参数（教科书默认值）
_K1 = 1.5
_B = 0.75


def load_kb() -> list[dict]:
    """加载知识库条目列表。"""
    if not config.KB_FILE.exists():
        raise FileNotFoundError(
            f"知识库文件不存在：{config.KB_FILE}。请先运行 python tools/seed_demo.py 初始化示例数据。")
    return json.loads(config.KB_FILE.read_text(encoding="utf-8"))


def tokenize(text: str) -> list[str]:
    """中文分词 + 去停用词。jieba 词典小、速度快，适合本地离线场景。"""
    tokens = []
    for token in jieba.lcut(text.lower()):
        token = token.strip()
        if not token:
            continue
        if token in _STOPWORDS:
            continue
        if re.fullmatch(r"[\W_]+", token):  # 纯标点/符号丢弃
            continue
        tokens.append(token)
    return tokens


class BM25:
    """BM25 检索器（教科书式实现）。

    只索引知识条的 question + tags + category 文本；answer 不参与索引，
    避免“答案越长越容易被命中”的偏置。
    """

    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        self.doc_tokens = [
            tokenize(" ".join([d.get("question", ""), d.get("category", ""),
                               " ".join(d.get("tags", []))]))
            for d in docs
        ]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / len(docs) if docs else 0.0
        df: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            df.update(set(tokens))
        self.df = df
        self.n = len(docs)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)

    def scores(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        result: list[float] = []
        for i, tokens in enumerate(self.doc_tokens):
            tf = Counter(tokens)
            score = 0.0
            for term in query_tokens:
                if term not in tf:
                    continue
                f = tf[term]
                denom = f + _K1 * (1 - _B + _B * self.doc_len[i] / max(self.avgdl, 1e-9))
                score += self._idf(term) * f * (_K1 + 1) / denom
            result.append(round(score, 4))
        return result


def search_kb(query: str, top_k: int | None = None) -> list[dict]:
    """检索知识库，返回按相关度降序的 top_k 条（含检索得分）。"""
    top_k = top_k or config.KB_TOP_K
    docs = load_kb()
    scores = BM25(docs).scores(query)
    ranked = sorted(zip(scores, docs), key=lambda item: item[0], reverse=True)
    hits = []
    for score, doc in ranked:
        if score <= 0:
            continue  # 完全不相关（无共同词）的条目不返回
        hits.append({"id": doc["id"], "category": doc["category"],
                     "question": doc["question"], "answer": doc["answer"],
                     "tags": doc.get("tags", []), "score": score})
        if len(hits) >= top_k:
            break
    return hits
