# -*- coding: utf-8 -*-
"""
=====================================================================
模型训练脚本（train_models.py）
=====================================================================
【这个文件做什么】
读取 data/processed 里预处理好的数据，训练并保存下面 4 个模型到
backend/models/artifacts/（系统运行时 predictor / anomaly_detector 加载的就是它们）：

  1. tey_model.json            —— XGBoost 回归：8 项运行参数 → 能量产出 TEY
  2. co_model.json             —— XGBoost 回归：9 项特征(含 TEY) → CO 排放
  3. nox_model.json            —— XGBoost 回归：9 项特征(含 TEY) → NOX 排放
  4. isolation_forest.joblib   —— 孤立森林：9 项特征做工况异常检测
另外生成 train_report.json，记录每个模型的评估指标（前端“模型信息”会读取）。

【训练策略（重要，答辩可能问）】
- 部署模型用【全量数据】训练（2011—2015 全部 36726 条），训练时内部随机留 10% 评估。
  原因：上线预测应尽量用上全部历史数据；且探查发现 NOX 存在“跨年数据漂移”
  （2011—2013 均值约 68-70，2014—2015 约 60 mg/m³），严格按年切分会让模型系统性高估，
  全量训练能兼顾演示可用性。
- 同时额外做一套【按年跨年外推】评估（用 2011—2014 训练、2015 测试），如实反映模型
  对“未来年份”的外推能力，不回避漂移问题。

运行方式：
  cd backend
  python train_models.py        # 或在项目根：python -m backend.train_models
=====================================================================
"""
import os
import json
import time                                   # 统计训练耗时
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split     # 切分训练集/测试集
from xgboost import XGBRegressor                          # XGBoost 回归模型
from sklearn.ensemble import IsolationForest              # 孤立森林异常检测模型
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error  # 三种评估指标
import joblib                                            # 保存/加载 sklearn 模型

import config
import data_loader                                       # 自己写的数据加载器

ARTIFACTS = config.MODEL_DIR                             # 模型产物输出目录（短别名）


def _metrics(y_true, y_pred):
    """【内部工具】计算三个回归评估指标并保留 4 位小数。
    y_true=真实值，y_pred=模型预测值：
      R²(决定系数)：越接近 1 越好，代表模型解释了多少数据变化；
      MAE(平均绝对误差)：预测平均偏多少，越小越好；
      RMSE(均方根误差)：对大误差更敏感，越小越好。"""
    return {
        'r2': round(float(r2_score(y_true, y_pred)), 4),
        'mae': round(float(mean_absolute_error(y_true, y_pred)), 4),
        'rmse': round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }


def _make_xgb():
    """【内部工厂】统一创建一个参数相同的 XGBoost 模型，保证三个模型设置一致。"""
    return XGBRegressor(
        n_estimators=600,          # 共 600 棵树
        learning_rate=0.05,        # 学习率：每棵树贡献的步长，小一点更稳
        max_depth=6,               # 每棵树最大深度，限制复杂度、防止死记硬背（过拟合）
        subsample=0.9,             # 每棵树随机用 90% 样本，增加泛化能力
        colsample_bytree=0.9,      # 每棵树随机用 90% 特征
        random_state=42,           # 固定随机种子，结果可复现
        early_stopping_rounds=50,  # 早停：连续 50 轮没提升就停止，避免无效训练
        eval_metric='rmse',        # 用 RMSE 作为训练过程中的评估标准
    )


def train_deployment(df):
    """用全量数据训练“上线部署用”的 3 个 XGBoost + 1 个孤立森林，并随机留 10% 评估。"""
    X8, X9, tey, co, nox = data_loader.get_features_targets(df)  # 拆出输入和真实答案

    report = {}    # 收集评估指标
    models = {}    # 收集训练好的模型（本函数内使用）

    # ---- TEY 模型：输入 8 特征 ----
    m = _make_xgb()
    # train_test_split：随机切出 90% 训练、10% 测试（test_size=0.1）
    X_tr, X_te, y_tr, y_te = train_test_split(X8, tey, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)  # fit=训练；verbose=False 关闭冗长日志
    m.save_model(os.path.join(ARTIFACTS, 'tey_model.json'))    # 保存模型到磁盘
    models['tey'] = m
    report['tey'] = {'模型': 'XGBoost(8特征→TEY)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # ---- CO 模型：输入 9 特征（含 TEY）----
    m = _make_xgb()
    X_tr, X_te, y_tr, y_te = train_test_split(X9, co, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    m.save_model(os.path.join(ARTIFACTS, 'co_model.json'))
    models['co'] = m
    report['co'] = {'模型': 'XGBoost(9特征→CO)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # ---- NOX 模型：输入 9 特征（含 TEY）----
    m = _make_xgb()
    X_tr, X_te, y_tr, y_te = train_test_split(X9, nox, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    m.save_model(os.path.join(ARTIFACTS, 'nox_model.json'))
    models['nox'] = m
    report['nox'] = {'模型': 'XGBoost(9特征→NOX)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # ---- 孤立森林：用全部 9 特征学习“正常工况”的分布，不使用标签 ----
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1)
    # n_estimators=树的数量；contamination=预期异常占比 5%；n_jobs=-1=用满 CPU 核
    iso.fit(X9)
    joblib.dump(iso, os.path.join(ARTIFACTS, 'isolation_forest.joblib'))  # sklearn 模型用 joblib 存
    report['isolation_forest'] = {
        '模型': 'IsolationForest(9特征)',
        'contamination': 0.05,
        # predict 返回 1/-1，(结果==-1).mean() 即被判为异常的样本占比
        '训练集异常比例': round(float((iso.predict(X9) == -1).mean()), 4),
    }
    return models, report


def train_cross_year():
    """跨年外推评估：用 2011—2014 训练、2015 测试，检验对未来年份的泛化能力。"""
    df = data_loader.load_combined()
    tr = df[df['year'].astype(int) <= 2014]   # 布尔筛选：年份≤2014 的作为训练
    te = df[df['year'].astype(int) == 2015]   # 年份=2015 的作为测试
    X8_tr, X9_tr, tey_tr, co_tr, nox_tr = data_loader.get_features_targets(tr)
    X8_te, X9_te, tey_te, co_te, nox_te = data_loader.get_features_targets(te)

    res = {}
    # 用列表把三个目标的“名字/训练输入/训练答案/测试输入/测试答案”打包，循环训练评估
    for name, Xtr, ytr, Xte, yte in [
        ('tey', X8_tr, tey_tr, X8_te, tey_te),   # TEY 用 8 特征
        ('co', X9_tr, co_tr, X9_te, co_te),      # CO/NOX 用 9 特征
        ('nox', X9_tr, nox_tr, X9_te, nox_te),
    ]:
        m = _make_xgb()
        m.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
        res[name] = _metrics(yte, m.predict(Xte))   # 在 2015 数据上打分
    return res


def main():
    """主流程：读数据 → 全量训练 → 跨年评估 → 写报告文件 → 打印结果。"""
    t0 = time.time()                                    # 记录开始时间
    df = data_loader.load_combined()
    print(f'加载全量数据: {len(df)} 条')

    os.makedirs(ARTIFACTS, exist_ok=True)

    # 1. 全量训练部署模型
    print('训练部署模型（全量数据）...')
    _, report = train_deployment(df)                    # 模型已存盘，这里只取评估报告

    # 2. 跨年外推评估（用来披露数据漂移的影响）
    print('计算按年跨年外推指标（train=2011-2014, test=2015）...')
    report['跨年外推评估'] = train_cross_year()
    report['跨年外推说明'] = (
        '训练集=2011-2014，测试集=2015。NOX 存在跨年数据漂移'
        '（2011-2013 均值约68-70 mg/m3，2014-2015 约60 mg/m3），'
        '按年外推时 NOX 预测会系统性偏高；部署模型采用全量数据训练以兼顾实时预测场景。'
    )

    # 3. 补充数据规模、耗时等元信息
    report['数据规模'] = {'全量': int(len(df)), '特征数': len(config.FEATURES_9), '目标': config.TARGET_COLS}
    report['训练耗时_秒'] = round(time.time() - t0, 2)
    # 把整份报告写成 JSON（indent=2 带缩进，方便人看）
    with open(os.path.join(ARTIFACTS, 'train_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 4. 在控制台打印两套指标，方便训练时直接查看
    print('\n===== 部署模型（全量训练）随机留出评估 =====')
    for k in ['tey', 'co', 'nox']:
        r = report[k]['随机留出评估']
        print(f"  {report[k]['模型']}: R2={r['r2']}, MAE={r['mae']}, RMSE={r['rmse']}")
    print(f"  IsolationForest: 异常比例={report['isolation_forest']['训练集异常比例']}")
    print('\n===== 按年跨年外推评估（披露漂移） =====')
    for k in ['tey', 'co', 'nox']:
        r = report['跨年外推评估'][k]
        print(f"  {k}: R2={r['r2']}, MAE={r['mae']}, RMSE={r['rmse']}")
    print(f'\n模型已保存至: {ARTIFACTS}，训练耗时 {report["训练耗时_秒"]}s')


# 直接运行本脚本时执行 main；被 import 时不自动训练
if __name__ == '__main__':
    main()
