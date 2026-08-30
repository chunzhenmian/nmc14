# -*- coding: utf-8 -*-
"""
工业燃气轮机 NOx/CO 排放数据集 - 数据预处理脚本
=================================================
功能：
  1. 合并 data/raw/ 下 2011-2015 五个年度 CSV
  2. 数据质量检查（缺失值 / 重复行 / 物理合理性）
  3. 去重清洗
  4. 按年份划分 训练(2011-2013) / 验证(2014) / 测试(2015) 集
     —— 时序数据按年份切分，避免随机切分造成的信息泄漏
  5. 特征标准化（StandardScaler 仅在训练集上拟合，避免泄漏），保存 scaler
  6. 输出预处理后数据文件到 data/processed/ 及预处理报告

输出文件：
  gt_combined.csv            合并去重后的全量数据（含 year 列）
  train.csv / val.csv / test.csv      原始数值的三分集（特征+目标+year）
  train_scaled.csv / val_scaled.csv / test_scaled.csv   标准化特征版
  scaler.joblib               特征标准化器（模型开发阶段复用）
  preprocess_report.json      预处理报告（数据量、清洗记录、统计信息）

运行方式：
  python scripts/preprocess.py
"""
import os
import json
import glob
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib

# -------------------- 路径与参数配置 --------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
OUT_DIR = os.path.join(BASE_DIR, 'data', 'processed')
os.makedirs(OUT_DIR, exist_ok=True)

# 特征列（9 项运行参数，含能量产出，用于 CO/NOX 预测）
FEATURE_COLS = ['AT', 'AP', 'AH', 'AFDP', 'GTEP', 'TIT', 'TAT', 'TEY', 'CDP']
# 目标列（排放浓度）
TARGET_COLS = ['CO', 'NOX']

# 按年份划分：训练 2011-2013，验证 2014，测试 2015
TRAIN_YEARS = ['2011', '2012', '2013']
VAL_YEARS = ['2014']
TEST_YEARS = ['2015']


def load_and_merge():
    """读取并合并各年度 CSV，添加 year 列"""
    files = sorted(glob.glob(os.path.join(RAW_DIR, 'gt_*.csv')))
    if not files:
        raise FileNotFoundError(f'未在 {RAW_DIR} 找到原始数据文件')
    frames = []
    for f in files:
        year = os.path.basename(f).split('_')[1].split('.')[0]
        df = pd.read_csv(f)
        df['year'] = year
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True)
    return merged


def quality_check(df):
    """数据质量检查，返回检查结果字典"""
    report = {
        '总样本数': int(len(df)),
        '缺失值总数': int(df[FEATURE_COLS + TARGET_COLS].isna().sum().sum()),
        '重复行数': int(df.duplicated().sum()),
        '各年份样本数': df['year'].value_counts().sort_index().to_dict(),
    }
    # 缺失值明细
    missing_detail = df[FEATURE_COLS + TARGET_COLS].isna().sum()
    report['缺失值明细'] = {str(k): int(v) for k, v in missing_detail[missing_detail > 0].items()}
    # 物理合理性检查：压力/温度等必须为正
    positive_cols = ['AP', 'AFDP', 'GTEP', 'TIT', 'TAT', 'CDP', 'CO', 'NOX']
    report['物理合理性检查'] = {}
    for c in positive_cols:
        bad = int((df[c] <= 0).sum())
        report['物理合理性检查'][c] = {'非正数数量': bad}
    # 环境温度可为负（冬季），单独说明
    report['物理合理性检查']['AT'] = {'负值数量': int((df['AT'] < 0).sum()), '说明': '环境温度可为负值，属正常'}
    return report


def drop_duplicates(df, report):
    """删除重复行并记录"""
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report['去重后剩余样本数'] = int(len(df))
    report['删除重复行数'] = before - len(df)
    return df


def split_by_year(df):
    """按年份划分训练/验证/测试集"""
    train = df[df['year'].isin(TRAIN_YEARS)].reset_index(drop=True)
    val = df[df['year'].isin(VAL_YEARS)].reset_index(drop=True)
    test = df[df['year'].isin(TEST_YEARS)].reset_index(drop=True)
    return train, val, test


def main():
    report = {'预处理时间': pd.Timestamp.now().isoformat(),
              '数据源': 'UCI Gas Turbine CO and NOx Emission Data Set',
              '划分规则': 'train=2011-2013, val=2014, test=2015'}

    # 1. 读取合并
    df = load_and_merge()
    report.update(quality_check(df))

    # 2. 去重
    df = drop_duplicates(df, report)

    # 3. 保存合并清洗后的全量数据
    df.to_csv(os.path.join(OUT_DIR, 'gt_combined.csv'), index=False, encoding='utf-8')
    report['已保存_合并清洗数据'] = 'gt_combined.csv'

    # 4. 按年份划分
    train, val, test = split_by_year(df)
    report['训练集样本数'] = len(train)
    report['验证集样本数'] = len(val)
    report['测试集样本数'] = len(test)

    # 5. 保存原始数值划分（特征 + 目标 + year）
    for name, part in [('train', train), ('val', val), ('test', test)]:
        part.to_csv(os.path.join(OUT_DIR, f'{name}.csv'), index=False, encoding='utf-8')

    # 6. 特征标准化（仅在训练集上拟合 scaler）
    scaler = StandardScaler()
    scaler.fit(train[FEATURE_COLS])
    joblib.dump(scaler, os.path.join(OUT_DIR, 'scaler.joblib'))

    for name, part in [('train', train), ('val', val), ('test', test)]:
        scaled = part.copy()
        scaled[FEATURE_COLS] = scaler.transform(part[FEATURE_COLS])
        scaled.to_csv(os.path.join(OUT_DIR, f'{name}_scaled.csv'), index=False, encoding='utf-8')

    # 7. 统计信息（原始尺度）
    report['各列统计'] = df[FEATURE_COLS + TARGET_COLS].describe().round(4).to_dict()
    report['特征均值_标准化后'] = dict(zip(FEATURE_COLS, scaler.mean_.round(4)))
    report['特征标准差_标准化后'] = dict(zip(FEATURE_COLS, scaler.scale_.round(4)))

    # 8. 写出预处理报告
    report_path = os.path.join(OUT_DIR, 'preprocess_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print('预处理完成。输出目录:', OUT_DIR)
    print(f'  全量样本: {len(df)}  |  训练: {len(train)}  |  验证: {len(val)}  |  测试: {len(test)}')
    print(f'  缺失值: {report["缺失值总数"]}  |  删除重复行: {report["删除重复行数"]}')
    print(f'  报告已保存: preprocess_report.json')


if __name__ == '__main__':
    main()
