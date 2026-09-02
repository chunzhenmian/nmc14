# -*- coding: utf-8 -*-
"""
=====================================================================
RESTful API 路由层（routes.py）
=====================================================================
【这个文件做什么】
前端通过 HTTP 请求访问后端，这里定义“什么地址、用什么方式、进来后做什么”。
每个 @api.route 就是一个对外接口（也叫端点 endpoint）。
  · GET  = 从后端“取”数据（参数跟在网址后面 ?key=value）；
  · POST = 给后端“提交”数据（数据放在请求体里，通常是 JSON）。
接口本身只做三件事：校验输入 → 调业务层 business → 把结果转成 JSON 返回。

接口清单（统一前缀 /api，在下面 Blueprint 处设置）：
  GET  /api/health                健康检查（看后端是否活着）
  GET  /api/overview              运行总览（设备/统计/最近记录）
  POST /api/predict               排放预测（提交 8 项运行参数）
  POST /api/optimize              参数优化（PSO，可带基准参数）
  POST /api/anomaly/check         工况异常检测（提交 9 项特征）
  GET  /api/records               历史记录查询（?type=predict|optimize）
  GET  /api/anomalies             异常预警日志查询
  GET  /api/device                设备基础信息
  GET  /api/model/info            模型评估信息
=====================================================================
"""
from flask import Blueprint, request, jsonify
# Blueprint：蓝图，可以把一组接口打包，最后统一注册到 app 上
# request：拿到前端发来的请求数据；jsonify：把 Python 字典转成 JSON 响应

import config
from services import business   # 业务层：真正干活的调度逻辑

# 创建名为 api 的蓝图，url_prefix 表示本文件所有接口地址都自动加上 /api 前缀
api = Blueprint('api', __name__, url_prefix='/api')


def _require_fields(data, fields):
    """【内部工具】校验必填字段：逐个检查 data 里是否缺字段/值为空，返回缺失字段名列表。"""
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == '']
    return missing


@api.route('/health', methods=['GET'])     # 绑定地址 /api/health，只允许 GET 请求
def health():
    """健康检查：最简单的接口，返回固定 ok，用来确认后端已正常启动。"""
    return jsonify({'status': 'ok', 'service': 'GT-Emission-System', 'version': '1.0.0'})


@api.route('/overview', methods=['GET'])
def overview():
    """运行总览：调用业务层聚合首页所需全部数据。"""
    try:
        return jsonify(business.overview_service())
    except Exception as e:
        # 出错时返回 500 状态码和错误信息（500=服务器内部错误）
        return jsonify({'error': f'获取总览失败: {e}'}), 500


@api.route('/predict', methods=['POST'])
def predict():
    """排放预测：前端提交 8 项运行参数（AT/AP/AH/AFDP/GTEP/TIT/TAT/CDP）。"""
    # silent=True：请求体不是合法 JSON 时不报错而是返回 None，再用 or {} 兜底成空字典
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, config.FEATURES_8)   # 检查 8 项是否齐全
    if missing:
        # 400=客户端请求有误（缺参数），把缺了哪些字段告诉前端
        return jsonify({'error': f'缺少必填参数: {missing}'}), 400
    try:
        # 字典推导式：按固定顺序把 8 个字段统一转成浮点数（前端传来的可能是字符串）
        params8 = {c: float(data[c]) for c in config.FEATURES_8}
    except (TypeError, ValueError):
        # 只要有一个值无法转成数字（比如填了字母），就返回 400
        return jsonify({'error': '参数必须为数值'}), 400
    result = business.predict_service(params8)   # 交给业务层计算并存档
    return jsonify(result)                       # 默认 200=成功


@api.route('/optimize', methods=['POST'])
def optimize():
    """参数优化：可提交当前参数作为基准 baseline，返回 PSO 最优方案及前后对比。"""
    data = request.get_json(silent=True) or {}
    baseline = None
    # any(...)：只要提交的数据里含有任意一个运行参数，就认为用户想以当前参数为基准
    if any(k in data for k in config.FEATURES_8):
        try:
            baseline = {c: float(data[c]) for c in config.FEATURES_8}
        except (TypeError, ValueError):
            return jsonify({'error': '基准参数必须为数值'}), 400
    # 粒子数、迭代次数允许前端指定，不给就用默认 30/60
    n_particles = int(data.get('n_particles', 30))
    n_iterations = int(data.get('n_iterations', 60))
    result = business.optimize_service(baseline, n_particles, n_iterations)
    return jsonify(result)


@api.route('/anomaly/check', methods=['POST'])
def anomaly_check():
    """工况异常检测：提交 9 项特征（8 项 + TEY）。"""
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
    """历史记录查询：?type=predict|optimize 筛选类型，?limit= 控制条数。"""
    rtype = request.args.get('type')                        # 取网址 ?type= 后面的值
    limit = min(int(request.args.get('limit', 50)), 200)    # 默认50条，最多200条，防止一次取太多
    return jsonify(business.records_service(rtype, limit))


@api.route('/anomalies', methods=['GET'])
def anomalies():
    """异常预警日志查询。"""
    limit = min(int(request.args.get('limit', 50)), 200)
    return jsonify(business.anomalies_service(limit))


@api.route('/device', methods=['GET'])
def device():
    """设备基础信息查询。函数内再导入 get_db 属于延迟导入，避免文件顶部循环依赖。"""
    from database.db import get_db
    # get_device_basics 查不到时返回 None，用 or {} 兜底成空字典，避免前端拿到 null
    return jsonify(get_db().get_device_basics() or {})


@api.route('/model/info', methods=['GET'])
def model_info():
    """模型评估指标查询（R²/MAE/RMSE 等）。"""
    return jsonify(business.model_info_service())
