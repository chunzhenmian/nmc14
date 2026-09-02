# -*- coding: utf-8 -*-
"""
=====================================================================
工况异常检测模块（anomaly_detector.py）
        ——技术方向 3：无监督学习 / 异常检测（孤立森林 Isolation Forest）
=====================================================================
【这个文件做什么】
给一组当前运行参数，判断它是不是“偏离正常工况”的异常，并给出预警等级和文字说明。

【为什么用“无监督”】
异常样本极少且形态多变，没法像预测那样靠大量“标准答案”训练，所以只用正常数据
建立“正常长什么样”的基准，谁明显偏离基准谁就是异常。

【孤立森林通俗理解】
随机反复地按某个特征的某个阈值切分数据：正常点扎堆，要切很多刀才能被单独分出来；
异常点本来就离群，很少几刀就能被“孤立”。模型给每个样本一个异常分值，
越容易被孤立、分值越负，就越异常。模型训练在 train_models.py，这里只加载使用。
=====================================================================
"""
import os                # 拼模型路径
import numpy as np       # 数值数组
import joblib            # joblib：用来加载/保存 sklearn 模型（这里加载 .joblib 文件）

import config            # 特征列名、模型目录配置


# 预警分级阈值：模型给出的 score 越负越异常（来自 IsolationForest 的 decision_function）
# 列表按从严重到轻微排列，比对时谁先满足就返回谁
ALERT_LEVELS = [
    (-0.35, '红色预警'),   # score ≤ -0.35：高度异常
    (-0.20, '橙色预警'),   # score ≤ -0.20：中度异常
    (-0.10, '黄色预警'),   # score ≤ -0.10：轻度异常
]
NORMAL_LEVEL = '正常'      # 模型判为正常时统一用这个文案


class AnomalyDetector:
    """孤立森林工况异常检测器：内部持有一个训练好的 IsolationForest 模型。"""

    def __init__(self, model_dir=None):
        self.model_dir = model_dir or config.MODEL_DIR  # 模型目录，默认取 config
        self.model = None     # 模型占位，load() 时载入
        self.loaded = False   # 是否已加载标记

    def load(self):
        """从磁盘加载训练好的孤立森林模型（joblib 格式）。"""
        self.model = joblib.load(os.path.join(self.model_dir, 'isolation_forest.joblib'))
        self.loaded = True
        return self

    def check(self, params9):
        """对单条工况做异常检测（最常用的对外方法）。
        params9：9 项特征组成的字典（比预测多一个 TEY）。
        返回：是否异常、异常分值、预警等级、文字描述。"""
        if not self.loaded:                 # 懒加载，第一次用才读模型
            self.load()
        # 按固定列名顺序取出 9 个数值，转成 1 行 9 列的二维数组（双层 [] = 1 个样本）
        x = np.asarray([[float(params9[c]) for c in config.FEATURES_9]])
        score = float(self.model.decision_function(x)[0])  # 异常分值：越负越异常
        pred = int(self.model.predict(x)[0])              # 模型直接给的判定：1=正常，-1=异常
        is_anomaly = pred == -1                           # -1 即异常，转成 True/False
        level = self._level(score, is_anomaly)            # 结合分值细分预警颜色等级
        return {
            'is_anomaly': is_anomaly,        # 是否异常（布尔值）
            'score': round(score, 4),        # 分值保留 4 位小数，便于前端展示
            'level': level,                  # 正常/黄色/橙色/红色预警
            'description': self._describe(level, score),  # 对应的中文处置建议
        }

    def _level(self, score, is_anomaly):
        """内部方法：先看是否异常，再按异常分值落到具体颜色等级。"""
        if not is_anomaly:                  # 模型都说正常，直接返回正常
            return NORMAL_LEVEL
        for thr, lv in ALERT_LEVELS:        # 从红→橙→黄依次比对分值
            if score <= thr:
                return lv
        return '黄色预警'                    # 判为异常但分值没到橙/红阈值，归为最轻的黄色

    @staticmethod
    def _describe(level, score):
        """静态工具：把等级翻译成给运维人员看的处置建议文案。"""
        desc = {
            '正常': '工况处于正常范围，未见异常。',
            '黄色预警': '工况偏离正常分布，建议关注运行参数变化。',
            '橙色预警': '工况明显偏离正常分布，建议核查关键运行参数并安排巡检。',
            '红色预警': '工况严重偏离正常分布，建议立即排查设备状态并采取干预措施。',
        }
        return desc.get(level, '')  # 按等级取文案，找不到就返回空串

    def anomaly_contribution(self, params9, baseline=None):
        """【辅助分析】定位“是哪些参数偏离得最厉害”。
        做法：把当前样本每个特征与正常基准（如中位数）比较，算相对偏差并从大到小排序，
        偏差最大的特征就是最可疑的异常来源。"""
        if baseline is None:
            baseline = {}                    # 没给基准就用空字典，后面会逐项跳过
        feats = config.FEATURES_9
        contrib = {}
        for c in feats:
            v = float(params9[c])            # 当前值
            b = baseline.get(c)              # 基准值
            if b is None:
                continue                     # 没有基准的特征无法比较，跳过
            # 相对偏差=|当前-基准| / |基准|；分母加 1e-6 防止基准为 0 时除零
            dev = abs(v - b) / (abs(b) + 1e-6)
            contrib[c] = round(dev, 4)
        # sorted 按偏差值（kv[1]）从大到小（reverse=True）排序，最异常的特征排最前
        return dict(sorted(contrib.items(), key=lambda kv: kv[1], reverse=True))


def get_detector():
    """【单例模式】全局只加载一次异常检测器并复用（模型读盘较慢，避免重复加载）。"""
    if not hasattr(get_detector, '_instance'):
        get_detector._instance = AnomalyDetector().load()
    return get_detector._instance
