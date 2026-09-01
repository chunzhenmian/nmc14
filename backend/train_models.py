# -*- coding: utf-8 -*-
"""
模型训练脚本
=============
使用 data/processed 预处理数据训练以下模型并保存到 backend/models/artifacts/：

  1. tey_model.json     —— XGBoost 回归，8 项运行参数 → 涡轮能量产出 TEY
  2. co_model.json      —— XGBoost 回归，9 项特征(含 TEY) → CO 排放
  3. nox_model.json     —— XGBoost 回归，9 项特征(含 TEY) → NOX 排放
  4. isolation_forest.joblib —— 孤立森林，9 项特征工况异常检测

训练策略说明
------------
- 部署模型采用【全量数据训练】(2011-2015 全部 36726 条)，内部随机留出 10% 评估。
  理由：实时预测场景下应使用全部历史数据；同时经探查发现 NOX 存在跨年数据漂移
  (2011-2013 均值 68-70 vs 2014-2015 约 60)，按年外推会系统性高估，
  全量训练可兼顾演示可用性与说明漂移现象。
- 同时报告【按年跨年外推】指标(train=2011-2014, test=2015)，如实披露外推能力。

运行方式：python -m backend.train_models
"""
import os
import json
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import IsolationForest
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib

from . import config
from . import data_loader

ARTIFACTS = config.MODEL_DIR


def _metrics(y_true, y_pred):
    return {
        'r2': round(float(r2_score(y_true, y_pred)), 4),
        'mae': round(float(mean_absolute_error(y_true, y_pred)), 4),
        'rmse': round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }


def _make_xgb():
    return XGBRegressor(
        n_estimators=600, learning_rate=0.05, max_depth=6,
        subsample=0.9, colsample_bytree=0.9, random_state=42,
        early_stopping_rounds=50, eval_metric='rmse',
    )


def train_deployment(df):
    """全量数据训练部署模型 + 随机留出评估"""
    X8, X9, tey, co, nox = data_loader.get_features_targets(df)

    report = {}
    models = {}

    # TEY 模型
    m = _make_xgb()
    X_tr, X_te, y_tr, y_te = train_test_split(X8, tey, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    m.save_model(os.path.join(ARTIFACTS, 'tey_model.json'))
    models['tey'] = m
    report['tey'] = {'模型': 'XGBoost(8特征→TEY)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # CO 模型
    m = _make_xgb()
    X_tr, X_te, y_tr, y_te = train_test_split(X9, co, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    m.save_model(os.path.join(ARTIFACTS, 'co_model.json'))
    models['co'] = m
    report['co'] = {'模型': 'XGBoost(9特征→CO)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # NOX 模型
    m = _make_xgb()
    X_tr, X_te, y_tr, y_te = train_test_split(X9, nox, test_size=0.1, random_state=42)
    m.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    m.save_model(os.path.join(ARTIFACTS, 'nox_model.json'))
    models['nox'] = m
    report['nox'] = {'模型': 'XGBoost(9特征→NOX)', '随机留出评估': _metrics(y_te, m.predict(X_te))}

    # 孤立森林
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1)
    iso.fit(X9)
    joblib.dump(iso, os.path.join(ARTIFACTS, 'isolation_forest.joblib'))
    report['isolation_forest'] = {
        '模型': 'IsolationForest(9特征)',
        'contamination': 0.05,
        '训练集异常比例': round(float((iso.predict(X9) == -1).mean()), 4),
    }
    return models, report


def train_cross_year():
    """按年跨年外推评估：train=2011-2014, test=2015"""
    df = data_loader.load_combined()
    tr = df[df['year'].astype(int) <= 2014]
    te = df[df['year'].astype(int) == 2015]
    X8_tr, X9_tr, tey_tr, co_tr, nox_tr = data_loader.get_features_targets(tr)
    X8_te, X9_te, tey_te, co_te, nox_te = data_loader.get_features_targets(te)

    res = {}
    for name, Xtr, ytr, Xte, yte in [
        ('tey', X8_tr, tey_tr, X8_te, tey_te),
        ('co', X9_tr, co_tr, X9_te, co_te),
        ('nox', X9_tr, nox_tr, X9_te, nox_te),
    ]:
        m = _make_xgb()
        m.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
        res[name] = _metrics(yte, m.predict(Xte))
    return res


def main():
    t0 = time.time()
    df = data_loader.load_combined()
    print(f'加载全量数据: {len(df)} 条')

    os.makedirs(ARTIFACTS, exist_ok=True)

    # 1. 全量训练部署模型
    print('训练部署模型（全量数据）...')
    _, report = train_deployment(df)

    # 2. 跨年外推评估（披露数据漂移影响）
    print('计算按年跨年外推指标（train=2011-2014, test=2015）...')
    report['跨年外推评估'] = train_cross_year()
    report['跨年外推说明'] = (
        '训练集=2011-2014，测试集=2015。NOX 存在跨年数据漂移'
        '（2011-2013 均值约68-70 mg/m3，2014-2015 约60 mg/m3），'
        '按年外推时 NOX 预测会系统性偏高；部署模型采用全量数据训练以兼顾实时预测场景。'
    )

    report['数据规模'] = {'全量': int(len(df)), '特征数': len(config.FEATURES_9), '目标': config.TARGET_COLS}
    report['训练耗时_秒'] = round(time.time() - t0, 2)
    with open(os.path.join(ARTIFACTS, 'train_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

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


if __name__ == '__main__':
    main()
