# -*- coding: utf-8 -*-
"""数据加载器：从 data/processed 读取预处理后的训练/验证/测试数据"""
import os
import pandas as pd
from . import config

PROCESSED = config.DATA_PROCESSED


def load_split(name='train'):
    """加载指定划分（train/val/test）的原始数值数据，返回 DataFrame（含 year 列）"""
    path = os.path.join(PROCESSED, f'{name}.csv')
    if not os.path.exists(path):
        raise FileNotFoundError(f'未找到预处理数据: {path}，请先运行 scripts/preprocess.py')
    return pd.read_csv(path)


def load_combined():
    """加载合并去重后的全量数据"""
    path = os.path.join(PROCESSED, 'gt_combined.csv')
    if not os.path.exists(path):
        raise FileNotFoundError(f'未找到合并数据: {path}')
    return pd.read_csv(path)


def get_features_targets(df):
    """拆分为特征与目标"""
    X8 = df[config.FEATURES_8].values
    X9 = df[config.FEATURES_9].values
    y_tey = df['TEY'].values
    y_co = df['CO'].values
    y_nox = df['NOX'].values
    return X8, X9, y_tey, y_co, y_nox
