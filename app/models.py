from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SQLRequest(BaseModel):
    question: str = Field(min_length=1)
    context: str = ""


class QueryRequest(SQLRequest):
    sql: Optional[str] = None
    include_chart: bool = False
    include_report: bool = False


class RecordsRequest(BaseModel):
    records: List[Dict[str, Any]]


class TrendRequest(RecordsRequest):
    date_col: str
    value_col: str


class ChartRequest(RecordsRequest):
    question: str = "对比"
    x_col: Optional[str] = None
    y_col: Optional[str] = None


class ReportRequest(SQLRequest):
    sql: Optional[str] = None
