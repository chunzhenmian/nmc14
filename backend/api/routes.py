# -*- coding: utf-8 -*-
"""
RESTful API 路由
================
接口清单：
  GET  /api/health                健康检查
  GET  /api/overview              运行总览（设备/统计/最近记录）
  POST /api/predict               排放预测（8 项运行参数）
  POST /api/optimize              参数优化（PSO，可带基准参数）
  POST /api/anomaly/check         工况异常检测（9 项特征）
  GET  /api/records               历史记录查询（?type=predict|optimize）
  GET  /api/anomalies             异常预警日志查询
  GET  /api/device                设备基础信息
  GET  /api/model/info            模型评估信息
"""
from flask import Blueprint, request, jsonify

from .. import config
from ..services import business

api = Blueprint('api', __name__, url_prefix='/api')


def _require_fields(data, fields):
    """校验必填字段，返回缺失字段列表"""
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == '']
    return missing


@api.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'GT-Emission-System', 'version': '1.0.0'})


@api.route('/overview', methods=['GET'])
def overview():
    try:
        return jsonify(business.overview_service())
    except Exception as e:
        return jsonify({'error': f'获取总览失败: {e}'}), 500


@api.route('/predict', methods=['POST'])
def predict():
    """排放预测：输入 8 项运行参数（AT/AP/AH/AFDP/GTEP/TIT/TAT/CDP）"""
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, config.FEATURES_8)
    if missing:
        return jsonify({'error': f'缺少必填参数: {missing}'}), 400
    try:
        params8 = {c: float(data[c]) for c in config.FEATURES_8}
    except (TypeError, ValueError):
        return jsonify({'error': '参数必须为数值'}), 400
    result = business.predict_service(params8)
    return jsonify(result)


@api.route('/optimize', methods=['POST'])
def optimize():
    """参数优化：可选传基准参数 baseline，返回最优方案与对比"""
    data = request.get_json(silent=True) or {}
    baseline = None
    if any(k in data for k in config.FEATURES_8):
        try:
            baseline = {c: float(data[c]) for c in config.FEATURES_8}
        except (TypeError, ValueError):
            return jsonify({'error': '基准参数必须为数值'}), 400
    n_particles = int(data.get('n_particles', 30))
    n_iterations = int(data.get('n_iterations', 60))
    result = business.optimize_service(baseline, n_particles, n_iterations)
    return jsonify(result)


@api.route('/anomaly/check', methods=['POST'])
def anomaly_check():
    """工况异常检测：输入 9 项特征（含 TEY）"""
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, config.FEATURES_9)
    if missing:
        return jsonify({'error': f'缺少必填参数: {missing}'}), 400
    try:
        params9 = {c: float(data[c]) for c in config.FEATURES_9}
    except (TypeError, ValueError):
        return jsonify({'error': '参数必须为数值'}), 400
    result = business.anomaly_service(params9)
    return jsonify(result)


@api.route('/records', methods=['GET'])
def records():
    rtype = request.args.get('type')
    limit = min(int(request.args.get('limit', 50)), 200)
    return jsonify(business.records_service(rtype, limit))


@api.route('/anomalies', methods=['GET'])
def anomalies():
    limit = min(int(request.args.get('limit', 50)), 200)
    return jsonify(business.anomalies_service(limit))


@api.route('/device', methods=['GET'])
def device():
    from ..database.db import get_db
    return jsonify(get_db().get_device_basics() or {})


@api.route('/model/info', methods=['GET'])
def model_info():
    return jsonify(business.model_info_service())
