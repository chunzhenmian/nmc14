# -*- coding: utf-8 -*-
"""
=====================================================================
业务服务层（business.py）
=====================================================================
【这个文件做什么】
它处在“接口层 routes.py”和“算法/数据库”之间，像一个调度员：
  接口只负责收发数据，不关心怎么算；算法模块只负责计算，不关心存不存库。
  业务层把它们串起来——调用对应算法 → 拿到结果 → 顺手存进数据库 → 把结果返回。

分层的好处：各管一摊、逻辑清晰，以后换算法或换数据库都不影响接口。
=====================================================================
"""
from models.predictor import get_predictor          # 排放预测器（单例）
from models.optimizer import get_optimizer          # PSO 优化器（单例）
from models.anomaly_detector import get_detector    # 异常检测器（单例）
from database.db import get_db                       # 数据库连接（单例）
import config                                        # 配置（排放限值等）


def predict_service(params8):
    """排放预测业务：输入 8 参数 → 输出 TEY/CO/NOX + 等级，并把本次记录存档。"""
    predictor = get_predictor()                 # 拿到预测器（全局只加载一次）
    result = predictor.full_predict(params8)    # 完成“预测+评级+达标判断”一条龙
    db = get_db()                               # 拿到数据库连接
    try:
        db.add_run_record('predict', params8, result)  # 把输入和结果写进运行记录表
    except Exception as e:
        # 存档失败不影响把预测结果返回给用户，只在结果里附带一条警告
        result['db_warning'] = f'记录存档失败: {e}'
    return result


def optimize_service(params8=None, n_particles=30, n_iterations=60):
    """参数优化业务：用 PSO 找最优参数，并把优化方案存档。
    params8 为空时表示不设基准、纯随机搜索；有值时会做“优化前后对比”。"""
    optimizer = get_optimizer(n_particles=n_particles, n_iterations=n_iterations)
    baseline = params8 if params8 else None    # 空字典/None 都视为没有基准
    result = optimizer.optimize(baseline=baseline)  # 执行粒子群寻优
    db = get_db()
    try:
        db.add_run_record('optimize', {'baseline': params8}, result)  # 存优化记录
    except Exception as e:
        result['db_warning'] = f'记录存档失败: {e}'
    return result


def anomaly_service(params9):
    """异常检测业务：判定工况是否异常、给预警等级，并写入异常日志表。"""
    detector = get_detector()
    result = detector.check(params9)           # 得到是否异常/分值/等级/描述
    db = get_db()
    try:
        # 日志里记录：输入参数、异常分值、等级、文字描述
        db.add_anomaly_log(params9, result['score'], result['level'], result['description'])
    except Exception as e:
        result['db_warning'] = f'日志写入失败: {e}'
    return result


def overview_service():
    """运行总览业务：把首页要用的设备信息、统计数字、最近记录一次性聚合好返回。"""
    db = get_db()
    device = db.get_device_basics()            # 机组基础档案
    stats = db.stats()                         # 各类记录条数统计
    try:
        recent_predict = db.get_records('predict', limit=10)    # 最近 10 条预测
        recent_optimize = db.get_records('optimize', limit=5)    # 最近 5 条优化
        recent_anomaly = db.get_anomaly_logs(limit=10)           # 最近 10 条异常
    except Exception as e:
        # 查最近记录失败时，用空列表兜底，保证总览主体仍能显示
        recent_predict, recent_optimize, recent_anomaly = [], [], []
        stats['error'] = str(e)
    return {
        'device': device,
        'stats': stats,
        'recent_predict': recent_predict,
        'recent_optimize': recent_optimize,
        'recent_anomaly': recent_anomaly,
        'emission_limits': config.EMISSION_LIMITS,  # 顺便把排放限值给前端展示
    }


def records_service(record_type=None, limit=50):
    """历史运行/优化记录查询业务：record_type 可筛选 predict/optimize，不传则查全部。"""
    db = get_db()
    return db.get_records(record_type, limit)


def anomalies_service(limit=50):
    """异常预警日志查询业务。"""
    db = get_db()
    return db.get_anomaly_logs(limit)


def model_info_service():
    """读取训练时生成的 train_report.json（含各模型 R²/MAE/RMSE 等评估指标），
    供前端“模型信息”展示。"""
    import json   # 放在函数内导入，属于按需使用的标准库
    import os
    path = os.path.join(config.MODEL_DIR, 'train_report.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:  # encoding 指定 utf-8，防止中文乱码
            return json.load(f)                        # 把 JSON 文件解析成 Python 字典
    return {'error': '未找到模型训练报告'}
