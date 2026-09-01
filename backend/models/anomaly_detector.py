# -*- coding: utf-8 -*-
"""
工况异常检测模块（技术方向 3：无监督学习 / 异常检测 - 孤立森林）
================================================================
基于正常工况数据构建监测基准，识别偏离正常分布的工况异常与排放异常，
输出异常分值、预警等级与关键异常特征定位。
"""
import os
import numpy as np
import joblib

from .. import config


# 预警分级：score 越负越异常（IsolationForest decision_function）
ALERT_LEVELS = [
    (-0.35, '红色预警'),   # 高度异常
    (-0.20, '橙色预警'),   # 中度异常
    (-0.10, '黄色预警'),   # 轻度异常
]
NORMAL_LEVEL = '正常'


class AnomalyDetector:
    """孤立森林工况异常检测器"""

    def __init__(self, model_dir=None):
        self.model_dir = model_dir or config.MODEL_DIR
        self.model = None
        self.loaded = False

    def load(self):
        self.model = joblib.load(os.path.join(self.model_dir, 'isolation_forest.joblib'))
        self.loaded = True
        return self

    def check(self, params9):
        """单样本异常检测
        params9: 9 项特征 dict（含 TEY）
        返回：异常分值、是否异常、预警等级
        """
        if not self.loaded:
            self.load()
        x = np.asarray([[float(params9[c]) for c in config.FEATURES_9]])
        score = float(self.model.decision_function(x)[0])   # 越负越异常
        pred = int(self.model.predict(x)[0])                 # 1 正常, -1 异常
        is_anomaly = pred == -1
        level = self._level(score, is_anomaly)
        return {
            'is_anomaly': is_anomaly,
            'score': round(score, 4),
            'level': level,
            'description': self._describe(level, score),
        }

    def _level(self, score, is_anomaly):
        if not is_anomaly:
            return NORMAL_LEVEL
        for thr, lv in ALERT_LEVELS:
            if score <= thr:
                return lv
        return '黄色预警'

    @staticmethod
    def _describe(level, score):
        desc = {
            '正常': '工况处于正常范围，未见异常。',
            '黄色预警': '工况偏离正常分布，建议关注运行参数变化。',
            '橙色预警': '工况明显偏离正常分布，建议核查关键运行参数并安排巡检。',
            '红色预警': '工况严重偏离正常分布，建议立即排查设备状态并采取干预措施。',
        }
        return desc.get(level, '')

    def anomaly_contribution(self, params9, baseline=None):
        """定位关键异常特征：比较该样本与正常基准(中位数)的偏差"""
        if baseline is None:
            baseline = {}
        feats = config.FEATURES_9
        contrib = {}
        for c in feats:
            v = float(params9[c])
            b = baseline.get(c)
            if b is None:
                continue
            # 归一化偏差（相对基准的比例）
            dev = abs(v - b) / (abs(b) + 1e-6)
            contrib[c] = round(dev, 4)
        return dict(sorted(contrib.items(), key=lambda kv: kv[1], reverse=True))


def get_detector():
    """单例获取异常检测器"""
    if not hasattr(get_detector, '_instance'):
        get_detector._instance = AnomalyDetector().load()
    return get_detector._instance
