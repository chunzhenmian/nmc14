# -*- coding: utf-8 -*-
"""
=====================================================================
数据加载器（data_loader.py）
=====================================================================
训练模型时，这个文件专门负责“把预处理好的 CSV 数据读进内存”，
并把一张表拆成“输入特征 X”和“预测目标 y”，供 train_models.py 使用。

可以把它理解为“数据搬运工”：自己不做算法，只负责把磁盘上的数据
按要求的格式整理好，交给训练脚本。
=====================================================================
"""
import os                 # 拼文件路径用
import pandas as pd       # pandas：处理表格数据的库，读进来的一张表叫 DataFrame
import config            # 读取数据目录等配置

# 预处理数据所在目录（来自 config，这里起个短名字方便下面用）
PROCESSED = config.DATA_PROCESSED


def load_split(name='train'):
    """读取某一个数据划分文件。
    name 可选 'train'（训练集）/ 'val'（验证集）/ 'test'（测试集）。
    返回 pandas DataFrame（就是一张带列名的表，里面还保留 year 年份列）。"""
    # 拼出完整文件路径，例如 .../data/processed/train.csv
    path = os.path.join(PROCESSED, f'{name}.csv')
    if not os.path.exists(path):  # 文件不存在时给出明确、可操作的报错
        raise FileNotFoundError(f'未找到预处理数据: {path}，请先运行 scripts/preprocess.py')
    return pd.read_csv(path)      # read_csv：把 CSV 文件读成 DataFrame 返回


def load_combined():
    """读取“合并去重后的全量数据” gt_combined.csv（2011—2015 全部 36726 条）。
    部署模型要用全部历史数据训练，所以需要这个全量文件。"""
    path = os.path.join(PROCESSED, 'gt_combined.csv')
    if not os.path.exists(path):
        raise FileNotFoundError(f'未找到合并数据: {path}')
    return pd.read_csv(path)


def get_features_targets(df):
    """把一张数据表拆成“模型输入 X”和“真实答案 y”。
    传入：df —— DataFrame 表
    返回 5 个数组：
      X8    —— 8 项运行参数（用于预测 TEY）
      X9    —— 9 项特征（8 项 + TEY，用于预测 CO/NOX）
      y_tey —— TEY 真实值
      y_co  —— CO 真实值
      y_nox —— NOX 真实值
    .values 表示只取数字部分、丢掉列名，转成 numpy 数组（模型只认数字数组）。"""
    X8 = df[config.FEATURES_8].values
    X9 = df[config.FEATURES_9].values
    y_tey = df['TEY'].values
    y_co = df['CO'].values
    y_nox = df['NOX'].values
    return X8, X9, y_tey, y_co, y_nox
