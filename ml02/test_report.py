import pytest
import json
import os
from data_models import ReportDataContract

OUTPUT_FILE = "report_data.json"

def test_json_file_exists():
    assert os.path.exists(OUTPUT_FILE), f"文件 {OUTPUT_FILE} 未生成！"

def test_json_schema_validation():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    report = ReportDataContract(**data)
    assert report is not None

def test_business_logic():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    report = ReportDataContract(**data)
    # 业务断言：总 PV 必须大于 0
    assert report.overview.pv > 0, "总计 PV 不应为空！"