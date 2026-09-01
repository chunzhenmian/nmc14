# -*- coding: utf-8 -*-
"""
排放预测模块（技术方向 1：监督学习 / 回归分析 - XGBoost）
==========================================================
输入 8 项运行参数 → 预测 TEY 能量产出 → 预测 CO / NOX 排放浓度 → 排放等级判定
"""
import os
import numpy as np
from xgboost import XGBRegressor

from .. import config
from .. import data_loader

# 排放等级阈值（mg/m³）
NOX_GRADE = [(50, '优'), (75, '良'), (100, '中')]   # >100 为差
CO_GRADE = [(10, '优'), (20, '良'), (30, '中')]     # >30 为差


class EmissionPredictor:
    """XGBoost 排放预测器（含 TEY 能量产出预测）"""

    def __init__(self, model_dir=None):
        self.model_dir = model_dir or config.MODEL_DIR
        self.tey_model = None
        self.co_model = None
        self.nox_model = None
        self.loaded = False

    def load(self):
        """加载训练好的模型"""
        self.tey_model = XGBRegressor()
        self.tey_model.load_model(os.path.join(self.model_dir, 'tey_model.json'))
        self.co_model = XGBRegressor()
        self.co_model.load_model(os.path.join(self.model_dir, 'co_model.json'))
        self.nox_model = XGBRegressor()
        self.nox_model.load_model(os.path.join(self.model_dir, 'nox_model.json'))
        self.loaded = True
        return self

    def predict_tey(self, params8):
        """预测涡轮能量产出 TEY（MW）"""
        x = np.asarray([params8], dtype=float).reshape(1, -1)
        return float(self.tey_model.predict(x)[0])

    def predict_emissions(self, params8, tey=None):
        """预测 CO / NOX 排放浓度（mg/m³）
        params8: 8 项运行参数 dict/array；tey: 若未提供则自动预测
        """
        if not self.loaded:
            self.load()
        p8 = [float(params8[c]) for c in config.FEATURES_8]
        if tey is None:
            tey = self.predict_tey(p8)
        p9 = p8 + [float(tey)]
        x = np.asarray([p9], dtype=float)
        co = float(self.co_model.predict(x)[0])
        nox = float(self.nox_model.predict(x)[0])
        return {'tey': float(tey), 'co': co, 'nox': nox}

    @staticmethod
    def grade_emission(co, nox):
        """排放等级判定"""
        def _grade(value, table):
            for limit, g in table:
                if value <= limit:
                    return g
            return '差'
        co_grade = _grade(co, CO_GRADE)
        nox_grade = _grade(nox, NOX_GRADE)
        # 综合等级取两者较差
        order = {'优': 1, '良': 2, '中': 3, '差': 4}
        overall = max([co_grade, nox_grade], key=lambda g: order[g])
        return {
            'overall': overall,
            'co_grade': co_grade,
            'nox_grade': nox_grade,
            'co_limit': config.EMISSION_LIMITS['CO'],
            'nox_limit': config.EMISSION_LIMITS['NOX'],
        }

    def full_predict(self, params8):
        """完整预测：8 参数 → TEY → CO/NOX → 等级"""
        res = self.predict_emissions(params8)
        res['grade'] = self.grade_emission(res['co'], res['nox'])
        res['standards_met'] = (res['co'] <= res['grade']['co_limit']
                                and res['nox'] <= res['grade']['nox_limit'])
        return res


def get_predictor():
    """单例获取预测器"""
    if not hasattr(get_predictor, '_instance'):
        get_predictor._instance = EmissionPredictor().load()
    return get_predictor._instance
