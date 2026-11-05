# 数据分析 Agent

这是根据《项目4：数据分析Agent》实现的一个可运行 Python 服务，覆盖 PDF 中的核心链路：自然语言转 SQL、数据分析、趋势分析、数据清洗、自动图表和结构化报告。

## 快速启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000/docs> 查看交互式 API 文档。

服务默认使用 `data/demo.db` 中的订单示例数据，不需要配置大模型密钥即可体验。接入外部 LLM 时，可以把一个实现 `call(messages) -> str` 的对象传给 `NL2SQLConverter`。

## 主要接口

- `GET /health`：健康检查
- `GET /schema`：查看当前数据库结构
- `POST /sql`：将自然语言问题转换成只读 SQL
- `POST /query`：转换并执行查询，可选生成图表和报告
- `POST /clean`：清洗一组 JSON 记录
- `POST /trend`：计算时间序列趋势
- `POST /chart`：根据问题生成 Plotly 图表
- `POST /report`：生成结构化分析报告

示例：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/query -Method Post -ContentType 'application/json' -Body '{"question":"去年华北区的销售额是多少？","include_chart":true,"include_report":true}'
```

## 目录结构

```text
app/
  main.py       FastAPI 入口与 API
  engine.py     SQL 执行、摘要、清洗和趋势分析
  nl2sql.py     Few-shot NL2SQL 和无模型回退策略
  charts.py     Plotly 自动图表生成
  report.py     结构化报告生成
  storage.py    SQLite 示例库和 Schema 读取
  seed.py       初始化示例数据
data/demo.csv   示例订单数据
docker-compose.yml
```

生产环境应在数据库层配置只读账号，并增加敏感字段脱敏、查询审计和导出权限控制。
