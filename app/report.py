from __future__ import annotations

from typing import Any, Dict


def build_report(question: str, query_result: Dict[str, Any]) -> Dict[str, Any]:
    if not query_result.get("success"):
        return {"title": "数据分析报告", "question": question, "status": "failed", "error": query_result.get("error")}
    summary = query_result.get("summary", {})
    numeric = summary.get("numeric_columns", [])
    observations = []
    for item in numeric:
        if item.get("min") is not None and item.get("max") is not None:
            observations.append(f"{item['name']} 范围为 {item['min']:.2f} 至 {item['max']:.2f}，平均值为 {item['mean']:.2f}。")
    return {
        "title": "数据分析报告",
        "question": question,
        "status": "success",
        "overview": {"row_count": query_result.get("row_count", 0), "columns": query_result.get("columns", [])},
        "observations": observations or ["结果中没有可直接计算的数值字段。"],
        "summary": summary,
    }
