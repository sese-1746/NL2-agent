from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional


class NL2SQLConverter:
    """把自然语言问题转换为 SQL。

    传入 ``llm`` 时使用 Few-shot 提示词；没有模型时使用可解释的规则回退，
    这样项目在本地也能完整演示。
    """

    def __init__(self, llm: Optional[Callable[[List[Dict[str, str]]], str]], database_schema: dict):
        self.llm = llm
        self.schema = database_schema
        self.examples = self._load_examples()

    def _load_examples(self) -> List[dict]:
        return [
            {
                "question": "北京市 2023 年的总销售额是多少？",
                "sql": "SELECT SUM(amount) AS total_amount FROM orders WHERE city = '北京' AND strftime('%Y', date) = '2023'",
            },
            {
                "question": "订单数量最多的前 5 个客户是谁？",
                "sql": "SELECT customer_id, COUNT(*) AS order_count FROM orders GROUP BY customer_id ORDER BY order_count DESC LIMIT 5",
            },
        ]

    def _format_schema(self) -> str:
        sections = []
        for table, columns in self.schema.items():
            lines = [f"## {table}"]
            for col in columns:
                description = col.get("description", "")
                lines.append(f"- {col['name']}: {col.get('type', 'unknown')} {description}".strip())
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    def _prompt(self, question: str, context: str) -> str:
        examples = "\n".join(f"Q: {e['question']}\nSQL: {e['sql']}" for e in self.examples)
        return f"""你是 SQL 专家，只输出一条标准、只读 SQL 查询。

数据库结构：
{self._format_schema()}

示例：
{examples}

问题：{question}
补充上下文：{context}
要求：只输出 SQL，不要 Markdown 或解释；仅允许 SELECT 或 WITH 查询。"""

    def convert(self, question: str, context: str = "") -> str:
        if not question.strip():
            raise ValueError("问题不能为空")
        if self.llm:
            response = self.llm([
                {"role": "system", "content": "你是一个 SQL 专家。"},
                {"role": "user", "content": self._prompt(question, context)},
            ])
            return self._extract_sql(response)
        return self._fallback_sql(question)

    def _fallback_sql(self, question: str) -> str:
        table = "orders" if "orders" in self.schema else next(iter(self.schema), "orders")
        q = question.lower().replace(" ", "")
        conditions = []
        city_map = {"北京": "北京", "上海": "上海", "广州": "广州", "深圳": "深圳", "华北": "华北"}
        for key, value in city_map.items():
            if key in question:
                conditions.append(f"city = '{value}'")
                break
        year = re.search(r"(20\d{2})", question)
        if year:
            conditions.append(f"strftime('%Y', date) = '{year.group(1)}'")
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        if any(k in q for k in ("总销售额", "销售总额", "销售额是多少", "金额总和")):
            return f"SELECT SUM(amount) AS total_amount FROM {table}{where}"
        if any(k in q for k in ("平均销售额", "平均金额")):
            return f"SELECT AVG(amount) AS average_amount FROM {table}{where}"
        if "订单数量" in q or "订单数" in q:
            if "客户" in q:
                limit = re.search(r"前(\d+)", question)
                n = limit.group(1) if limit else "10"
                return f"SELECT customer_id, COUNT(*) AS order_count FROM {table}{where} GROUP BY customer_id ORDER BY order_count DESC LIMIT {n}"
            return f"SELECT COUNT(*) AS order_count FROM {table}{where}"
        if "趋势" in q or "变化" in q:
            return f"SELECT date, SUM(amount) AS total_amount FROM {table}{where} GROUP BY date ORDER BY date"
        return f"SELECT * FROM {table}{where} ORDER BY date DESC LIMIT 100"

    @staticmethod
    def _extract_sql(text: str) -> str:
        sql = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
        sql = sql.split("--", 1)[0].strip()
        match = re.search(r"\b(WITH|SELECT)\b[\s\S]*", sql, flags=re.IGNORECASE)
        if not match:
            raise ValueError("模型没有返回有效的 SELECT SQL")
        return match.group(0).strip().rstrip(";")
