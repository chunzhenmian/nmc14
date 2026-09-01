# -*- coding: utf-8 -*-
"""
参数优化模块（技术方向 2：智能优化算法 - 粒子群优化 PSO）
==========================================================
以排放达标为约束、最大化机组能量产出 TEY 为目标，
在参数合理区间内自动寻优 8 项关键运行参数。

优化流程：PSO 搜索 8 参数 → 预测 TEY → 预测 CO/NOX → 检查约束 → 计算适应度
"""
import numpy as np

from .predictor import get_predictor
from .. import config


class PSOOptimizer:
    """粒子群优化器：目标为最大化 TEY，约束为 CO/NOX 排放达标"""

    def __init__(self, n_particles=30, n_iterations=60,
                 w=0.7, c1=1.5, c2=1.5, seed=42):
        self.n_particles = n_particles
        self.n_iterations = n_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.seed = seed
        self.bounds = config.PARAM_BOUNDS
        self.dim = len(config.FEATURES_8)
        self.params_name = config.FEATURES_8
        self.predictor = None

    def _clip(self, x):
        lb = np.array([self.bounds[p][0] for p in self.params_name])
        ub = np.array([self.bounds[p][1] for p in self.params_name])
        return np.clip(x, lb, ub)

    def _fitness(self, x):
        """适应度：TEY 最大化；排放超标时施加惩罚"""
        p8 = dict(zip(self.params_name, x))
        res = self.predictor.predict_emissions(p8)   # 内部会先预测 TEY
        tey = res['tey']
        co, nox = res['co'], res['nox']
        co_limit = config.EMISSION_LIMITS['CO']
        nox_limit = config.EMISSION_LIMITS['NOX']
        penalty = 0.0
        if co > co_limit:
            penalty += (co - co_limit) / co_limit * 50
        if nox > nox_limit:
            penalty += (nox - nox_limit) / nox_limit * 50
        return tey - penalty

    def optimize(self, baseline=None):
        """执行 PSO 寻优，返回最优方案与效果评估
        baseline: 可选，基准参数（用于对比优化前后效果）
        """
        if self.predictor is None:
            self.predictor = get_predictor()

        rng = np.random.default_rng(self.seed)
        lb = np.array([self.bounds[p][0] for p in self.params_name])
        ub = np.array([self.bounds[p][1] for p in self.params_name])

        # 初始化粒子
        x = rng.uniform(lb, ub, size=(self.n_particles, self.dim))
        if baseline is not None:
            x[0] = [baseline[p] for p in self.params_name]
        v = rng.uniform(-(ub - lb) * 0.1, (ub - lb) * 0.1, size=x.shape)

        pbest = x.copy()
        pbest_fit = np.array([self._fitness(p) for p in pbest])
        gbest = pbest[int(np.argmax(pbest_fit))].copy()
        gbest_fit = float(np.max(pbest_fit))

        for _ in range(self.n_iterations):
            r1 = rng.random(size=x.shape)
            r2 = rng.random(size=x.shape)
            v = (self.w * v + self.c1 * r1 * (pbest - x) + self.c2 * r2 * (gbest - x))
            x = self._clip(x + v)
            fits = np.array([self._fitness(p) for p in x])
            improve = fits > pbest_fit
            pbest[improve] = x[improve]
            pbest_fit[improve] = fits[improve]
            if float(fits.max()) > gbest_fit:
                gbest = x[int(np.argmax(fits))].copy()
                gbest_fit = float(fits.max())

        return self._build_result(gbest, baseline)

    def _build_result(self, best, baseline=None):
        """构造优化结果：最优参数 + 预测排放 + 与基准对比"""
        best_p8 = dict(zip(self.params_name, [round(float(v), 3) for v in best]))
        pred = self.predictor.full_predict(best_p8)

        result = {
            'optimal_params': best_p8,
            'prediction': pred,
            'standards_met': pred['standards_met'],
        }
        # 基准对比
        if baseline is not None:
            base_p8 = {p: float(baseline[p]) for p in self.params_name}
            base_pred = self.predictor.full_predict(base_p8)
            result['baseline'] = {
                'params': base_p8,
                'prediction': base_pred,
            }
            result['improvement'] = {
                'tey_delta': round(pred['tey'] - base_pred['tey'], 3),
                'tey_pct': round((pred['tey'] - base_pred['tey']) / base_pred['tey'] * 100, 2) if base_pred['tey'] else 0,
                'co_delta': round(pred['co'] - base_pred['co'], 3),
                'nox_delta': round(pred['nox'] - base_pred['nox'], 3),
            }
        return result


def get_optimizer(**kwargs):
    """单例获取优化器"""
    if not hasattr(get_optimizer, '_instance'):
        get_optimizer._instance = PSOOptimizer(**kwargs)
    return get_optimizer._instance
