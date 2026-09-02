# -*- coding: utf-8 -*-
"""
=====================================================================
排放预测模块（predictor.py）——技术方向 1：监督学习 / 回归（XGBoost）
=====================================================================
【这个文件做什么】
用户在前端填入 8 项运行参数，这里负责算出三件事：
  ① 预测机组能量产出 TEY；
  ② 再结合 TEY 预测 CO、NOX 两种污染物浓度；
  ③ 根据浓度评出“优/良/中/差”排放等级。

【为什么分两步（两阶段预测链）】
数据里 CO/NOX 与“能量产出 TEY”关系密切，所以先用 8 个运行参数预测 TEY，
再把“8 个参数 + 刚预测出的 TEY”共 9 项喂给 CO、NOX 模型，精度更高。

【XGBoost 是什么（小白版）】
可以理解成“很多棵决策树一起投票”的模型：每棵树像一串“如果温度高…如果压力大…”
的判断题，成百上千棵树的结果加权汇总，得到最终的连续数值预测。模型不在这里训练，
训练在 train_models.py；这里只负责把训练好、存到磁盘的模型读出来用。
=====================================================================
"""
import os                       # 拼模型文件路径
import numpy as np              # numpy：高效数值计算库，模型输入要求是 numpy 数字数组
from xgboost import XGBRegressor  # XGBoost 的回归模型类（回归=预测一个连续数值）

import config                   # 配置：特征列名、模型目录、排放限值
import data_loader              # 数据加载器（本文件实际未直接调用，保留以便扩展）

# 排放等级阈值表（单位 mg/m³）。列表里是 (上限, 等级)，按从优到差顺序排列
NOX_GRADE = [(50, '优'), (75, '良'), (100, '中')]   # NOX：≤50优、≤75良、≤100中、>100差
CO_GRADE = [(10, '优'), (20, '良'), (30, '中')]     # CO：≤10优、≤20良、≤30中、>30差


class EmissionPredictor:
    """XGBoost 排放预测器：内部持有 TEY、CO、NOX 三个训练好的模型。"""

    def __init__(self, model_dir=None):
        # model_dir 不传就用 config 里的默认模型目录
        self.model_dir = model_dir or config.MODEL_DIR
        # 先把三个模型占位为空，等 load() 时才真正从磁盘读入
        self.tey_model = None
        self.co_model = None
        self.nox_model = None
        self.loaded = False     # 是否已加载模型的标记

    def load(self):
        """从磁盘加载三个训练好的模型文件（.json 是 XGBoost 模型的保存格式）。"""
        self.tey_model = XGBRegressor()  # 先建一个空模型对象
        self.tey_model.load_model(os.path.join(self.model_dir, 'tey_model.json'))  # 再把学到的参数装进去
        self.co_model = XGBRegressor()
        self.co_model.load_model(os.path.join(self.model_dir, 'co_model.json'))
        self.nox_model = XGBRegressor()
        self.nox_model.load_model(os.path.join(self.model_dir, 'nox_model.json'))
        self.loaded = True      # 标记为“已加载”
        return self             # 返回自身，方便链式调用

    def predict_tey(self, params8):
        """第一阶段：用 8 项运行参数预测涡轮能量产出 TEY（单位 MWh/MW 量级）。"""
        # np.asarray 把输入转成 numpy 数组；外层再套一层 []、reshape(1,-1) 是为了凑成
        # 模型要求的“二维形状”：1 行（1 个样本）× 8 列（8 个特征）
        x = np.asarray([params8], dtype=float).reshape(1, -1)
        # predict 返回数组（哪怕只有 1 个结果），[0] 取出第一个，float() 转成普通小数
        return float(self.tey_model.predict(x)[0])

    def predict_emissions(self, params8, tey=None):
        """第二阶段：预测 CO / NOX 排放浓度（mg/m³）。
        params8：8 项运行参数（字典或数组）；tey：可外部传入 TEY，不传则自动先预测。"""
        if not self.loaded:     # 懒加载：第一次用时若还没读模型，就先读
            self.load()
        # 严格按 config.FEATURES_8 的固定顺序取出 8 个数值（顺序必须和训练时一致！）
        p8 = [float(params8[c]) for c in config.FEATURES_8]
        if tey is None:                     # 没给 TEY 就先用第一阶段模型预测出来
            tey = self.predict_tey(p8)
        p9 = p8 + [float(tey)]              # 8 项后面拼上 TEY，凑成 9 项输入
        x = np.asarray([p9], dtype=float)   # 变成 1×9 的二维数组
        co = float(self.co_model.predict(x)[0])    # 预测 CO
        nox = float(self.nox_model.predict(x)[0])  # 预测 NOX
        return {'tey': float(tey), 'co': co, 'nox': nox}  # 打包成字典返回

    @staticmethod
    def grade_emission(co, nox):
        """【静态方法】根据 CO、NOX 浓度判定排放等级。静态方法=不依赖 self，可理解成独立小工具。"""
        def _grade(value, table):
            # 内部小函数：拿一个数值去等级表里比对，落在哪个区间就返回哪个等级
            for limit, g in table:
                if value <= limit:
                    return g
            return '差'        # 超过所有上限，就是最差
        co_grade = _grade(co, CO_GRADE)
        nox_grade = _grade(nox, NOX_GRADE)
        # 综合等级取两者中“较差”的那个（短板原则，只要一项差整体就不能算好）
        order = {'优': 1, '良': 2, '中': 3, '差': 4}  # 用数字表示好坏，数字越大越差
        # max 按 order 里的数字挑出更大（更差）的等级
        overall = max([co_grade, nox_grade], key=lambda g: order[g])
        return {
            'overall': overall,                    # 综合等级
            'co_grade': co_grade,                  # CO 单项等级
            'nox_grade': nox_grade,                # NOX 单项等级
            'co_limit': config.EMISSION_LIMITS['CO'],    # 附上标准限值，前端可直接展示
            'nox_limit': config.EMISSION_LIMITS['NOX'],
        }

    def full_predict(self, params8):
        """对外最常用的“一条龙”：8 参数 → 预测 TEY/CO/NOX → 评等级 → 判断是否达标。"""
        res = self.predict_emissions(params8)                 # 先拿到三个预测值
        res['grade'] = self.grade_emission(res['co'], res['nox'])  # 再补上等级
        # 是否同时满足 CO、NOX 都不超限值（and = 两个条件都成立才算达标）
        res['standards_met'] = (res['co'] <= res['grade']['co_limit']
                                and res['nox'] <= res['grade']['nox_limit'])
        return res


def get_predictor():
    """【单例模式】全局只创建一个预测器并反复复用。
    好处：模型文件较大，只读盘加载一次，之后所有请求共用，响应更快。
    hasattr(函数, '_instance')：看函数对象身上是否已经挂了 _instance 这个属性。"""
    if not hasattr(get_predictor, '_instance'):
        get_predictor._instance = EmissionPredictor().load()  # 没有就创建并加载
    return get_predictor._instance                           # 有的话直接返回同一个
