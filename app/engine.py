from __future__ import annotations

import ast
import re
from typing import Any, Dict

import pandas as pd


class DataAnalysisEngine:
    """查询、清洗、摘要和趋势分析引擎。"""

    def __init__(self) -> None:
        self.current_df: pd.DataFrame | None = None

    def execute_query(self, sql: str, connection) -> Dict[str, Any]:
        self._ensure_read_only(sql)
        try:
            df = pd.read_sql_query(sql, connection)
            self.current_df = df
            return {
                "success": True,
                "data": df.where(pd.notna(df), None).to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
                "summary": self.generate_summary(df),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _ensure_read_only(sql: str) -> None:
        normalized = re.sub(r"\s+", " ", sql.strip()).lower()
        if ";" in normalized.rstrip(";"):
            raise ValueError("只允许执行一条 SQL")
        if not re.match(r"^(select|with)\b", normalized):
            raise ValueError("只允许执行 SELECT 或 WITH 查询")
        blocked = r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace|truncate)\b"
        if re.search(blocked, normalized):
            raise ValueError("查询包含被禁止的写操作")

    def execute_python(self, code: str) -> Dict[str, Any]:
        """在受限上下文中处理当前 DataFrame；仅用于受信任的服务端代码。"""
        if self.current_df is None:
            return {"success": False, "error": "还没有可分析的数据"}
        local_vars = {"df": self.current_df.copy()}
        try:
            tree = ast.parse(code, mode="exec")
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    raise ValueError("不允许在分析代码中导入模块")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"open", "exec", "eval", "__import__"}:
                    raise ValueError("不允许调用文件或动态执行函数")
            exec(compile(tree, "<analysis>", "exec"), {"pd": pd, "__builtins__": {}}, local_vars)
            result: Dict[str, Any] = {"success": True}
            if "result" in local_vars:
                result["result"] = local_vars["result"]
            if isinstance(local_vars.get("df"), pd.DataFrame):
                result["data"] = local_vars["df"].where(pd.notna(local_vars["df"]), None).to_dict(orient="records")
            return result
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    def generate_summary(df: pd.DataFrame) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "numeric_columns": [],
            "categorical_columns": [],
        }
        for col in df.columns:
            series = df[col]
            if pd.api.types.is_numeric_dtype(series):
                summary["numeric_columns"].append({
                    "name": col,
                    "mean": _number(series.mean()),
                    "median": _number(series.median()),
                    "std": _number(series.std()),
                    "min": _number(series.min()),
                    "max": _number(series.max()),
                })
            else:
                summary["categorical_columns"].append({
                    "name": col,
                    "unique_count": int(series.nunique(dropna=True)),
                    "top_values": {str(k): int(v) for k, v in series.value_counts(dropna=True).head(5).items()},
                })
        return summary

    @staticmethod
    def clean_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        cleaned = df.copy()
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        for col in cleaned.columns:
            if pd.api.types.is_object_dtype(cleaned[col]):
                cleaned[col] = cleaned[col].map(lambda x: x.strip() if isinstance(x, str) else x)
                numeric = pd.to_numeric(cleaned[col], errors="coerce")
                if numeric.notna().mean() >= 0.8:
                    cleaned[col] = numeric
        for col in cleaned.select_dtypes(include="number").columns:
            median = cleaned[col].median()
            cleaned[col] = cleaned[col].fillna(median)
            q1, q3 = cleaned[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            if pd.notna(iqr) and iqr > 0:
                cleaned[col] = cleaned[col].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        cleaned = cleaned.where(pd.notna(cleaned), None)
        return {"success": True, "data": cleaned.to_dict(orient="records"), "row_count": len(cleaned), "removed_duplicates": before - len(cleaned), "summary": DataAnalysisEngine.generate_summary(cleaned)}

    @staticmethod
    def analyze_trends(df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
        if date_col not in df or value_col not in df:
            raise ValueError(f"找不到字段: {date_col} 或 {value_col}")
        work = df[[date_col, value_col]].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
        work = work.dropna().sort_values(date_col)
        values = work[value_col].tolist()
        rates = [(values[i] - values[i - 1]) / values[i - 1] * 100 if values[i - 1] else 0 for i in range(1, len(values))]
        avg = sum(rates) / len(rates) if rates else 0
        return {"trend": "increasing" if sum(rates) >= 0 else "decreasing", "avg_growth_rate": avg, "max_growth": max(rates) if rates else 0, "min_growth": min(rates) if rates else 0, "volatility": sum(abs(x - avg) for x in rates) / len(rates) if rates else 0, "points": [{"date": d.strftime("%Y-%m-%d"), "value": _number(v)} for d, v in zip(work[date_col], work[value_col])]}


def _number(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)
