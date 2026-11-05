from __future__ import annotations

from contextlib import closing

import pandas as pd
from fastapi import FastAPI, HTTPException

from .charts import ChartGenerator
from .engine import DataAnalysisEngine
from .models import ChartRequest, QueryRequest, RecordsRequest, ReportRequest, SQLRequest, TrendRequest
from .nl2sql import NL2SQLConverter
from .report import build_report
from .storage import connect, get_schema, init_database

app = FastAPI(title="数据分析 Agent", version="1.0.0", description="自然语言查询、分析、可视化和报告服务")
engine = DataAnalysisEngine()


@app.on_event("startup")
def startup() -> None:
    init_database()


def converter() -> NL2SQLConverter:
    return NL2SQLConverter(None, get_schema())


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-analysis-agent"}


@app.get("/schema")
def schema():
    return get_schema()


@app.post("/sql")
def to_sql(request: SQLRequest):
    try:
        return {"question": request.question, "sql": converter().convert(request.question, request.context)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/query")
def query(request: QueryRequest):
    try:
        sql = request.sql or converter().convert(request.question, request.context)
        with closing(connect()) as conn:
            result = engine.execute_query(sql, conn)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result["error"])
        response = {"question": request.question, "sql": sql, "result": result}
        if request.include_chart and result["data"]:
            response["chart"] = ChartGenerator(pd.DataFrame(result["data"])).auto_generate(request.question)
        if request.include_report:
            response["report"] = build_report(request.question, result)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/clean")
def clean(request: RecordsRequest):
    return engine.clean_dataframe(pd.DataFrame(request.records))


@app.post("/trend")
def trend(request: TrendRequest):
    try:
        return engine.analyze_trends(pd.DataFrame(request.records), request.date_col, request.value_col)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/chart")
def chart(request: ChartRequest):
    try:
        return ChartGenerator(pd.DataFrame(request.records)).auto_generate(request.question, request.x_col, request.y_col)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/report")
def report(request: ReportRequest):
    query_result = query(QueryRequest(question=request.question, context=request.context, sql=request.sql))
    return query_result | {"report": query_result.get("report") or build_report(request.question, query_result["result"])}
