# -*- coding: utf-8 -*-
"""
=====================================================================
后端 API 自动化测试（test_api.py，测试框架 pytest）
=====================================================================
【这个文件做什么】
不启动浏览器、不手动点按钮，而是用代码模拟前端向后端发请求，自动检查每个接口
返回的状态码和数据是否符合预期。每个以 test_ 开头的函数就是一条测试用例，
里面的 assert（断言）表示“我断定这里应该是这样”，不成立测试就失败。

运行方式：
  项目根：python -m pytest backend/tests -v
  或进入 backend：python -m pytest tests -v
覆盖：健康检查、排放预测、参数优化、异常检测、记录查询等共 11 条用例。
=====================================================================
"""
import os
import sys

# 把 backend 目录加入 sys.path，使包内“以 backend 为根”的绝对导入在测试中也可用
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)

import pytest

from app import create_app    # 后端应用工厂
import config

# 一组典型运行参数（取自数据集中位数附近），多个用例复用
TYPICAL = {
    'AT': 17.71, 'AP': 1013.07, 'AH': 77.87, 'AFDP': 3.93,
    'GTEP': 25.56, 'TIT': 1081.43, 'TAT': 546.16, 'CDP': 12.06,
}
# 9 项特征版：在 8 项基础上补一个 TEY（异常检测需要）
TYPICAL_9 = {**TYPICAL, 'TEY': 133.51}


# @pytest.fixture 是 pytest 的“夹具”：被测试函数当参数引用时，会自动先执行它并把返回值传入
@pytest.fixture()
def app():
    """创建一个用于测试的 Flask 应用。"""
    app = create_app()
    app.config['TESTING'] = True   # 打开测试模式（出错时能拿到更详细信息）
    return app


@pytest.fixture()
def client(app):
    """测试客户端：用它发请求就像真的访问后端，但不需要真的监听端口。"""
    return app.test_client()


# ---------- 健康检查 ----------
def test_health(client):
    r = client.get('/api/health')          # 模拟 GET 请求
    assert r.status_code == 200            # 断言状态码是 200（成功）
    body = r.get_json()                    # 取出 JSON 响应体
    assert body['status'] == 'ok'          # 断言其中 status 字段为 ok


# ---------- 排放预测 ----------
def test_predict_success(client):
    r = client.post('/api/predict', json=TYPICAL)   # 提交典型参数
    assert r.status_code == 200
    d = r.get_json()
    assert 'tey' in d and 'co' in d and 'nox' in d  # 三个结果字段都应存在
    # 数值合理性：能量产出与排放浓度应落在物理合理范围
    assert 80 < d['tey'] < 200
    assert 0 <= d['co'] < 60
    assert 0 < d['nox'] < 150
    assert d['grade']['overall'] in ('优', '良', '中', '差')  # 等级必须是四者之一


def test_predict_missing_params(client):
    # 故意只传一个参数，后端应返回 400（请求有误）
    r = client.post('/api/predict', json={'AT': 17.0})
    assert r.status_code == 400
    assert '缺少必填参数' in r.get_json()['error']


def test_predict_invalid_value(client):
    # 故意把温度填成非数字字符串，后端应返回 400
    bad = dict(TYPICAL)
    bad['AT'] = 'abc'
    r = client.post('/api/predict', json=bad)
    assert r.status_code == 400


# ---------- 参数优化 ----------
def test_optimize_success(client):
    r = client.post('/api/optimize', json={
        **TYPICAL, 'n_particles': 15, 'n_iterations': 20})  # 测试用较小规模，跑得快
    assert r.status_code == 200
    d = r.get_json()
    assert 'optimal_params' in d
    assert 'prediction' in d
    # 逐个检查优化后的参数没有越出 config 设定的边界（留 1e-3 浮点容差）
    for k, v in d['optimal_params'].items():
        assert config.PARAM_BOUNDS[k][0] - 1e-3 <= v <= config.PARAM_BOUNDS[k][1] + 1e-3
    # 传了基准参数，结果里应包含改善幅度对比
    assert 'improvement' in d
    assert 'tey_delta' in d['improvement']


# ---------- 异常检测 ----------
def test_anomaly_normal(client):
    r = client.post('/api/anomaly/check', json=TYPICAL_9)
    assert r.status_code == 200
    d = r.get_json()
    assert d['is_anomaly'] in (True, False)               # 布尔判定字段类型正确
    assert d['level'] in ('正常', '黄色预警', '橙色预警', '红色预警')  # 等级合法


def test_anomaly_extreme(client):
    # 故意构造一组明显偏离正常分布的极端工况，模型应判定为异常
    extreme = dict(TYPICAL_9)
    extreme['TIT'] = 900.0
    extreme['TEY'] = 40.0
    extreme['CDP'] = 5.0
    extreme['AFDP'] = 20.0
    r = client.post('/api/anomaly/check', json=extreme)
    assert r.status_code == 200
    assert r.get_json()['is_anomaly'] is True


# ---------- 记录与总览 ----------
def test_overview(client):
    r = client.get('/api/overview')
    assert r.status_code == 200
    d = r.get_json()
    assert 'device' in d and 'stats' in d   # 总览应包含设备信息和统计


def test_records_after_predict(client):
    # 先预测一次产生记录，再查预测记录，列表应至少有 1 条
    client.post('/api/predict', json=TYPICAL)
    r = client.get('/api/records?type=predict')
    assert r.status_code == 200
    assert len(r.get_json()) >= 1


def test_anomalies_log(client):
    # 先检测一次写日志，再查异常日志，应返回列表类型
    client.post('/api/anomaly/check', json=TYPICAL_9)
    r = client.get('/api/anomalies')
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_model_info(client):
    r = client.get('/api/model/info')
    assert r.status_code == 200
    d = r.get_json()
    assert 'tey' in d and 'co' in d and 'nox' in d   # 训练报告应含三个模型指标
