# -*- coding: utf-8 -*-
"""
=====================================================================
参数优化模块（optimizer.py）——技术方向 2：智能优化算法（粒子群 PSO）
=====================================================================
【这个文件做什么】
在“排放必须达标”的前提下，自动寻找一组运行参数，让机组能量产出 TEY 尽可能高。

【粒子群算法 PSO 通俗理解】
想象一群鸟（粒子）在一片山区找最高峰：
  · 每只鸟的“位置”就是一组 8 维运行参数（AT/AP/.../CDP）；
  · 山的“海拔高度”就是适应度（这里=TEY，越高越好；若排放超标就扣分，高度骤降）；
  · 每只鸟记得自己飞过的最高处（个体最优 pbest），也知道整群目前找到的最高处
    （全局最优 gbest）；
  · 每只鸟综合“惯性、飞回自己最好位置、飞向群体最好位置”三股力量调整速度和位置；
  · 反复迭代若干代，整群逐渐聚拢到最高峰附近，即得到近似最优参数。
=====================================================================
"""
import numpy as np                      # 数值计算：向量化地同时更新所有粒子，速度快

from models.predictor import get_predictor  # 复用预测器：每组参数都要靠它算 TEY/CO/NOX
import config                           # 参数边界、排放限值等配置


class PSOOptimizer:
    """粒子群优化器：目标=最大化 TEY，约束=CO/NOX 排放达标。"""

    def __init__(self, n_particles=30, n_iterations=60,
                 w=0.7, c1=1.5, c2=1.5, seed=42):
        self.n_particles = n_particles    # 粒子数量（鸟的只数），越多搜得越细但越慢
        self.n_iterations = n_iterations  # 迭代代数（飞多少轮）
        self.w = w                        # 惯性权重：保留原来飞行方向的程度
        self.c1 = c1                      # 个体学习因子：向“自己历史最优”靠拢的强度
        self.c2 = c2                      # 社会学习因子：向“群体全局最优”靠拢的强度
        self.seed = seed                  # 随机种子，固定后每次结果可复现
        self.bounds = config.PARAM_BOUNDS       # 8 个参数各自的上下限（搜索空间边界）
        self.dim = len(config.FEATURES_8)       # 维度 = 8（要优化 8 个参数）
        self.params_name = config.FEATURES_8    # 8 个参数的名字，按固定顺序
        self.predictor = None                    # 预测器延迟到优化时再获取

    def _clip(self, x):
        """把粒子位置“裁剪”回合法区间，防止参数跑出 config 设定的上下限。"""
        # 列表推导式按参数顺序取出每个参数的下限/上限，组成 numpy 数组
        lb = np.array([self.bounds[p][0] for p in self.params_name])  # lower bound 下限
        ub = np.array([self.bounds[p][1] for p in self.params_name])  # upper bound 上限
        return np.clip(x, lb, ub)  # 小于下限变下限、大于上限变上限，中间不变

    def _fitness(self, x):
        """【适应度函数】给某一组参数打分，分数越高越好。
        基础分=TEY 能量产出；一旦 CO 或 NOX 超标，就按超标比例扣分（惩罚），
        以此把“排放达标”这个硬约束揉进打分里。"""
        p8 = dict(zip(self.params_name, x))          # 把位置数组和参数名一一配成字典
        res = self.predictor.predict_emissions(p8)  # 用预测模型算这组参数的 TEY/CO/NOX
        tey = res['tey']
        co, nox = res['co'], res['nox']
        co_limit = config.EMISSION_LIMITS['CO']
        nox_limit = config.EMISSION_LIMITS['NOX']
        penalty = 0.0                                # 惩罚分初始为 0
        if co > co_limit:                           # CO 超标：超出比例越大扣得越多（×50 权重）
            penalty += (co - co_limit) / co_limit * 50
        if nox > nox_limit:                         # NOX 同理
            penalty += (nox - nox_limit) / nox_limit * 50
        return tey - penalty                        # 最终适应度=产出-惩罚，引导算法找“高产且达标”的解

    def optimize(self, baseline=None):
        """执行完整 PSO 寻优，返回最优方案及（可选的）与基准的对比结果。
        baseline：用户当前参数，传入的话会把它作为其中一个初始粒子并做前后对比。"""
        if self.predictor is None:                 # 第一次优化时获取预测器单例
            self.predictor = get_predictor()

        rng = np.random.default_rng(self.seed)     # 用固定种子创建随机数生成器（结果可复现）
        lb = np.array([self.bounds[p][0] for p in self.params_name])  # 各维下限
        ub = np.array([self.bounds[p][1] for p in self.params_name])  # 各维上限

        # ---- 初始化粒子位置：在上下限之间均匀随机撒点，形状=(粒子数, 维度)=(30,8) ----
        x = rng.uniform(lb, ub, size=(self.n_particles, self.dim))
        if baseline is not None:
            # 若给了基准参数，就把第 0 号粒子的初始位置设为基准（保证至少不劣于当前方案）
            x[0] = [baseline[p] for p in self.params_name]
        # 初始速度：在“跨度的 ±10%”范围内随机，避免一开始步子迈太大
        v = rng.uniform(-(ub - lb) * 0.1, (ub - lb) * 0.1, size=x.shape)

        # ---- 个体最优 pbest：刚开始时自己的位置就是自己的历史最优 ----
        pbest = x.copy()
        pbest_fit = np.array([self._fitness(p) for p in pbest])  # 每个粒子初始位置的适应度
        gbest = pbest[int(np.argmax(pbest_fit))].copy()         # argmax 找最高分粒子→全局最优位置
        gbest_fit = float(np.max(pbest_fit))                     # 全局最优分数

        # ---- 迭代更新（核心循环） ----
        for _ in range(self.n_iterations):
            r1 = rng.random(size=x.shape)   # 随机矩阵1（给个体学习项增加随机性）
            r2 = rng.random(size=x.shape)   # 随机矩阵2（给社会学习项增加随机性）
            # PSO 速度更新公式：新速度 = 惯性项 + 个体认知项 + 社会认知项（numpy 整体按元素并行计算）
            v = (self.w * v + self.c1 * r1 * (pbest - x) + self.c2 * r2 * (gbest - x))
            x = self._clip(x + v)           # 位置=旧位置+速度，并裁回合法边界
            fits = np.array([self._fitness(p) for p in x])  # 评估所有粒子新位置的适应度
            improve = fits > pbest_fit      # 找出本次比自己历史最优更好的粒子
            pbest[improve] = x[improve]     # 更新这些粒子的个体最优位置
            pbest_fit[improve] = fits[improve]  # 同步更新它们的个体最优分数
            if float(fits.max()) > gbest_fit:   # 若本轮出现比全局最优更好的
                gbest = x[int(np.argmax(fits))].copy()  # 更新全局最优位置
                gbest_fit = float(fits.max())           # 更新全局最优分数

        return self._build_result(gbest, baseline)  # 迭代结束，整理成结果返回

    def _build_result(self, best, baseline=None):
        """把最终最优位置整理成前端需要的结果字典：最优参数 + 预测结果 + 与基准对比。"""
        # 位置数组配回参数名，并把每个数值保留 3 位小数
        best_p8 = dict(zip(self.params_name, [round(float(v), 3) for v in best]))
        pred = self.predictor.full_predict(best_p8)  # 对最优参数做一次完整预测（含等级、达标）

        result = {
            'optimal_params': best_p8,       # 优化后的 8 个参数
            'prediction': pred,              # 这组参数对应的 TEY/CO/NOX/等级
            'standards_met': pred['standards_met'],  # 是否达标
        }
        # 如果用户传了基准参数，就计算“优化前 vs 优化后”的改善幅度
        if baseline is not None:
            base_p8 = {p: float(baseline[p]) for p in self.params_name}
            base_pred = self.predictor.full_predict(base_p8)  # 基准参数的预测结果
            result['baseline'] = {
                'params': base_p8,
                'prediction': base_pred,
            }
            # 差值=优化后-优化前；百分比=差值/优化前×100（分母为0时取0，防止除零报错）
            result['improvement'] = {
                'tey_delta': round(pred['tey'] - base_pred['tey'], 3),
                'tey_pct': round((pred['tey'] - base_pred['tey']) / base_pred['tey'] * 100, 2) if base_pred['tey'] else 0,
                'co_delta': round(pred['co'] - base_pred['co'], 3),
                'nox_delta': round(pred['nox'] - base_pred['nox'], 3),
            }
        return result


def get_optimizer(**kwargs):
    """【单例模式】全局只创建一个优化器复用。**kwargs 允许调用时覆盖默认参数
    （例如 n_particles=15）。"""
    if not hasattr(get_optimizer, '_instance'):
        get_optimizer._instance = PSOOptimizer(**kwargs)
    return get_optimizer._instance
