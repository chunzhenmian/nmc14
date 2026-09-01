# -*- coding: utf-8 -*-
"""
后端 API 自动化测试（pytest）
==============================
运行方式：python -m pytest backend/tests -v
覆盖：健康检查、排放预测、参数优化、异常检测、记录查询
"""
import os
import sys

# 保证可导入 backend 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from backend.app import create_app
from backend import config

# 一组典型运行参数（取自数据集中位数附近）
TYPICAL = {
    'AT': 17.71, 'AP': 1013.07, 'AH': 77.87, 'AFDP': 3.93,
    'GTEP': 25.56, 'TIT': 1081.43, 'TAT': 546.16, 'CDP': 12.06,
}
TYPICAL_9 = {**TYPICAL, 'TEY': 133.51}


@pytest.fixture()
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------- 健康检查 ----------
def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    body = r.get_json()
    assert body['status'] == 'ok'


# ---------- 排放预测 ----------
def test_predict_success(client):
    r = client.post('/api/predict', json=TYPICAL)
    assert r.status_code == 200
    d = r.get_json()
    assert 'tey' in d and 'co' in d and 'nox' in d
    # 数值合理性：能量产出与排放浓度在物理合理范围
    assert 80 < d['tey'] < 200
    assert 0 <= d['co'] < 60
    assert 0 < d['nox'] < 150
    assert d['grade']['overall'] in ('优', '良', '中', '差')


def test_predict_missing_params(client):
    # 缺参数应返回 400
    r = client.post('/api/predict', json={'AT': 17.0})
    assert r.status_code == 400
    assert '缺少必填参数' in r.get_json()['error']


def test_predict_invalid_value(client):
    # 非数值应返回 400
    bad = dict(TYPICAL)
    bad['AT'] = 'abc'
    r = client.post('/api/predict', json=bad)
    assert r.status_code == 400


# ---------- 参数优化 ----------
def test_optimize_success(client):
    r = client.post('/api/optimize', json={
        **TYPICAL, 'n_particles': 15, 'n_iterations': 20})
    assert r.status_code == 200
    d = r.get_json()
    assert 'optimal_params' in d
    assert 'prediction' in d
    # 输出参数个数与边界
    for k, v in d['optimal_params'].items():
        assert config.PARAM_BOUNDS[k][0] - 1e-3 <= v <= config.PARAM_BOUNDS[k][1] + 1e-3
    # 有基准对比时输出改善
    assert 'improvement' in d
    assert 'tey_delta' in d['improvement']


# ---------- 异常检测 ----------
def test_anomaly_normal(client):
    r = client.post('/api/anomaly/check', json=TYPICAL_9)
    assert r.status_code == 200
    d = r.get_json()
    assert d['is_anomaly'] in (True, False)
    assert d['level'] in ('正常', '黄色预警', '橙色预警', '红色预警')


def test_anomaly_extreme(client):
    # 构造明显偏离正常分布的工况
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
    assert 'device' in d and 'stats' in d


def test_records_after_predict(client):
    # 先预测一次，再查询记录应非空
    client.post('/api/predict', json=TYPICAL)
    r = client.get('/api/records?type=predict')
    assert r.status_code == 200
    assert len(r.get_json()) >= 1


def test_anomalies_log(client):
    client.post('/api/anomaly/check', json=TYPICAL_9)
    r = client.get('/api/anomalies')
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_model_info(client):
    r = client.get('/api/model/info')
    assert r.status_code == 200
    d = r.get_json()
    assert 'tey' in d and 'co' in d and 'nox' in d
