# -*- coding: utf-8 -*-
"""
业务服务层
==========
编排算法模块与数据库，提供：
  - 排放预测业务（含记录存档）
  - 参数优化业务（含记录存档）
  - 异常检测业务（含预警日志）
  - 总览数据聚合
"""
from ..models.predictor import get_predictor
from ..models.optimizer import get_optimizer
from ..models.anomaly_detector import get_detector
from ..database.db import get_db
from .. import config


def predict_service(params8):
    """排放预测业务：8 参数 → TEY/CO/NOX + 排放等级，并存档"""
    predictor = get_predictor()
    result = predictor.full_predict(params8)
    db = get_db()
    try:
        db.add_run_record('predict', params8, result)
    except Exception as e:
        result['db_warning'] = f'记录存档失败: {e}'
    return result


def optimize_service(params8=None, n_particles=30, n_iterations=60):
    """参数优化业务：PSO 寻优最优运行参数，并存档"""
    optimizer = get_optimizer(n_particles=n_particles, n_iterations=n_iterations)
    baseline = params8 if params8 else None
    result = optimizer.optimize(baseline=baseline)
    db = get_db()
    try:
        db.add_run_record('optimize', {'baseline': params8}, result)
    except Exception as e:
        result['db_warning'] = f'记录存档失败: {e}'
    return result


def anomaly_service(params9):
    """异常检测业务：判定工况异常与预警等级，并写日志"""
    detector = get_detector()
    result = detector.check(params9)
    db = get_db()
    try:
        db.add_anomaly_log(params9, result['score'], result['level'], result['description'])
    except Exception as e:
        result['db_warning'] = f'日志写入失败: {e}'
    return result


def overview_service():
    """运行总览：设备信息、记录统计、最近记录"""
    db = get_db()
    device = db.get_device_basics()
    stats = db.stats()
    try:
        recent_predict = db.get_records('predict', limit=10)
        recent_optimize = db.get_records('optimize', limit=5)
        recent_anomaly = db.get_anomaly_logs(limit=10)
    except Exception as e:
        recent_predict, recent_optimize, recent_anomaly = [], [], []
        stats['error'] = str(e)
    return {
        'device': device,
        'stats': stats,
        'recent_predict': recent_predict,
        'recent_optimize': recent_optimize,
        'recent_anomaly': recent_anomaly,
        'emission_limits': config.EMISSION_LIMITS,
    }


def records_service(record_type=None, limit=50):
    db = get_db()
    return db.get_records(record_type, limit)


def anomalies_service(limit=50):
    db = get_db()
    return db.get_anomaly_logs(limit)


def model_info_service():
    """返回模型评估信息（前端展示用）"""
    import json
    import os
    path = os.path.join(config.MODEL_DIR, 'train_report.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'error': '未找到模型训练报告'}
