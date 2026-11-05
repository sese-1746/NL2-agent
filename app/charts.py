from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class ChartGenerator:
    """根据问题关键词和字段类型选择 Plotly 图表。"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def auto_generate(self, question: str, x_col: Optional[str] = None, y_col: Optional[str] = None) -> dict:
        chart_type = self._select_chart_type(question)
        if chart_type == "heatmap":
            fig = self._heatmap()
        else:
            x_col, y_col = self._choose_columns(x_col, y_col, chart_type)
            if chart_type == "line":
                fig = px.line(self.df, x=x_col, y=y_col, title=f"{y_col} 随 {x_col} 的变化趋势")
            elif chart_type == "pie":
                fig = px.pie(self.df, names=x_col, values=y_col, title=f"{y_col} 按 {x_col} 的占比")
            elif chart_type == "scatter":
                fig = px.scatter(self.df, x=x_col, y=y_col, title=f"{x_col} 与 {y_col} 的关系")
            elif chart_type == "histogram":
                fig = px.histogram(self.df, x=x_col, title=f"{x_col} 的分布")
            else:
                fig = px.bar(self.df.sort_values(y_col, ascending=False), x=x_col, y=y_col, title=f"{y_col} 按 {x_col} 对比")
        fig.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
        return {"type": chart_type, "figure": fig.to_json(), "html": fig.to_html(full_html=False, include_plotlyjs="cdn")}

    def _select_chart_type(self, question: str) -> str:
        q = question.lower().replace(" ", "")
        if any(k in q for k in ("趋势", "变化", "时间")):
            return "line"
        if any(k in q for k in ("占比", "比例", "百分比", "分布")):
            return "pie" if "占比" in q or "比例" in q or "百分比" in q else "histogram"
        if any(k in q for k in ("相关", "关联", "关系")):
            return "scatter"
        if any(k in q for k in ("热力", "矩阵")):
            return "heatmap"
        return "bar"

    def _choose_columns(self, x_col: Optional[str], y_col: Optional[str], chart_type: str):
        if not len(self.df.columns):
            raise ValueError("数据没有字段")
        numeric = list(self.df.select_dtypes(include="number").columns)
        categorical = [c for c in self.df.columns if c not in numeric]
        x_col = x_col or (categorical[0] if categorical else self.df.columns[0])
        y_col = y_col or (numeric[0] if numeric else self.df.columns[-1])
        if x_col not in self.df.columns or (chart_type != "histogram" and y_col not in self.df.columns):
            raise ValueError("图表字段不存在")
        return x_col, y_col

    def _heatmap(self):
        numeric = self.df.select_dtypes(include="number")
        if numeric.empty:
            raise ValueError("热力图至少需要一个数值字段")
        corr = numeric.corr()
        return go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns, colorscale="RdBu_r", zmid=0), layout=dict(title="特征相关性热力图"))
