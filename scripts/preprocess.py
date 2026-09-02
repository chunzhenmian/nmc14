# -*- coding: utf-8 -*-
"""
=====================================================================
数据预处理脚本（preprocess.py）
=====================================================================
【这个文件做什么】
把从 UCI 下载的 5 个年度原始 CSV，清洗、切分、标准化后，变成模型能直接用的数据，
并生成一份预处理报告 preprocess_report.json。属于“建模前的备菜”步骤。

处理流程：
  1. 合并 data/raw/ 下 2011-2015 五个年度 CSV，并加 year 年份列；
  2. 数据质量检查（缺失值 / 重复行 / 物理合理性）；
  3. 删除完全重复的行；
  4. 按年份划分 训练(2011-2013) / 验证(2014) / 测试(2015)
     —— 时序数据按时间先后切，而不是随机打乱切，避免“用未来数据预测过去”的信息泄漏；
  5. 特征标准化（StandardScaler 只在训练集上学习均值方差，再套用到验证/测试，避免泄漏）；
  6. 输出处理后文件和预处理报告。

输出文件（都在 data/processed/）：
  gt_combined.csv                  合并去重后的全量数据（含 year 列）
  train/val/test.csv               原始数值的三个分集（特征+目标+year）
  *_scaled.csv                     对应标准化后的版本
  scaler.joblib                    标准化器（记录均值方差，开发阶段可复用）
  preprocess_report.json           预处理报告（数据量、清洗记录、统计信息）

运行方式：在项目根执行  python scripts/preprocess.py
=====================================================================
"""
import os
import json
import glob                                       # glob：按通配符批量找文件
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler  # 标准化工具：减均值除标准差
import joblib                                      # 保存 scaler

# -------------------- 路径与参数配置 --------------------
# 当前文件在 scripts/ 下，连续 dirname 两次退到项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')         # 原始数据目录
OUT_DIR = os.path.join(BASE_DIR, 'data', 'processed')  # 处理结果输出目录
os.makedirs(OUT_DIR, exist_ok=True)                    # 输出目录不存在就创建

# 9 项运行特征（注意这里含 TEY，用于 CO/NOX 建模；顺序按数据集原始列）
FEATURE_COLS = ['AT', 'AP', 'AH', 'AFDP', 'GTEP', 'TIT', 'TAT', 'TEY', 'CDP']
# 要预测的目标列：两种污染物浓度
TARGET_COLS = ['CO', 'NOX']

# 按年份划分：用前三年训练、第四年验证、最后一年测试（模拟“用过去预测未来”）
TRAIN_YEARS = ['2011', '2012', '2013']
VAL_YEARS = ['2014']
TEST_YEARS = ['2015']


def load_and_merge():
    """读取 data/raw 下所有 gt_20xx.csv 并纵向合并，同时从文件名提取年份加为 year 列。"""
    # glob 找出所有形如 gt_*.csv 的文件，sorted 保证按年份顺序
    files = sorted(glob.glob(os.path.join(RAW_DIR, 'gt_*.csv')))
    if not files:
        raise FileNotFoundError(f'未在 {RAW_DIR} 找到原始数据文件')
    frames = []                          # 收集每个年度的 DataFrame
    for f in files:
        # 文件名形如 gt_2011.csv，按下划线/点切分取出 '2011' 作为年份
        year = os.path.basename(f).split('_')[1].split('.')[0]
        df = pd.read_csv(f)
        df['year'] = year                # 新增一列 year，标记每行属于哪一年
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True)  # 纵向拼成一张大表，并重排行号
    return merged


def quality_check(df):
    """数据质量“体检”，统计缺失、重复、各年数量、物理合理性，结果放进报告字典。"""
    report = {
        '总样本数': int(len(df)),
        # isna() 找空值，两次 sum 分别按列、按表汇总成总数
        '缺失值总数': int(df[FEATURE_COLS + TARGET_COLS].isna().sum().sum()),
        '重复行数': int(df.duplicated().sum()),  # duplicated 标记重复行
        '各年份样本数': df['year'].value_counts().sort_index().to_dict(),  # 每年多少条
    }
    # 缺失值明细：哪些列有缺失、各缺多少（只保留>0的列）
    missing_detail = df[FEATURE_COLS + TARGET_COLS].isna().sum()
    report['缺失值明细'] = {str(k): int(v) for k, v in missing_detail[missing_detail > 0].items()}
    # 物理合理性检查：这些压力/温度/排放物理上不应为非正数
    positive_cols = ['AP', 'AFDP', 'GTEP', 'TIT', 'TAT', 'CDP', 'CO', 'NOX']
    report['物理合理性检查'] = {}
    for c in positive_cols:
        bad = int((df[c] <= 0).sum())     # 统计小于等于 0 的异常个数
        report['物理合理性检查'][c] = {'非正数数量': bad}
    # 环境温度 AT 冬季可能为负，属于正常，单独统计负值数量并加说明，不误判为错误
    report['物理合理性检查']['AT'] = {'负值数量': int((df['AT'] < 0).sum()), '说明': '环境温度可为负值，属正常'}
    return report


def drop_duplicates(df, report):
    """删除完全重复的行，并把删除数量记进报告。"""
    before = len(df)                                  # 去重前行数
    df = df.drop_duplicates().reset_index(drop=True)  # 去重并重排行索引
    report['去重后剩余样本数'] = int(len(df))
    report['删除重复行数'] = before - len(df)         # 前后差值=删掉的行数
    return df


def split_by_year(df):
    """按 year 列切出训练/验证/测试三个 DataFrame。"""
    train = df[df['year'].isin(TRAIN_YEARS)].reset_index(drop=True)  # isin：年份属于训练年份
    val = df[df['year'].isin(VAL_YEARS)].reset_index(drop=True)
    test = df[df['year'].isin(TEST_YEARS)].reset_index(drop=True)
    return train, val, test


def main():
    """预处理主流程，按步骤执行并最终写出所有文件与报告。"""
    report = {'预处理时间': pd.Timestamp.now().isoformat(),
              '数据源': 'UCI Gas Turbine CO and NOx Emission Data Set',
              '划分规则': 'train=2011-2013, val=2014, test=2015'}

    # 1. 读取并合并五个年度文件，然后做质量体检
    df = load_and_merge()
    report.update(quality_check(df))    # update：把体检结果合并进总报告

    # 2. 去重清洗
    df = drop_duplicates(df, report)

    # 3. 保存合并清洗后的全量数据（部署模型用全量训练时读它）；index=False 不额外保存行号列
    df.to_csv(os.path.join(OUT_DIR, 'gt_combined.csv'), index=False, encoding='utf-8')
    report['已保存_合并清洗数据'] = 'gt_combined.csv'

    # 4. 按年份切分三份
    train, val, test = split_by_year(df)
    report['训练集样本数'] = len(train)
    report['验证集样本数'] = len(val)
    report['测试集样本数'] = len(test)

    # 5. 先保存“原始数值”版本的三份数据（特征+目标+year）
    for name, part in [('train', train), ('val', val), ('test', test)]:
        part.to_csv(os.path.join(OUT_DIR, f'{name}.csv'), index=False, encoding='utf-8')

    # 6. 特征标准化。关键：scaler 只在训练集上 fit（学习均值、标准差）
    #    绝不能用验证/测试数据来 fit，否则等于提前偷看了答案，造成信息泄漏
    scaler = StandardScaler()
    scaler.fit(train[FEATURE_COLS])
    joblib.dump(scaler, os.path.join(OUT_DIR, 'scaler.joblib'))  # 保存标准化器备用

    # 用同一个 scaler 分别转换三份数据（验证/测试只 transform，不再 fit）
    for name, part in [('train', train), ('val', val), ('test', test)]:
        scaled = part.copy()                                    # 复制一份，不改原数据
        scaled[FEATURE_COLS] = scaler.transform(part[FEATURE_COLS])
        scaled.to_csv(os.path.join(OUT_DIR, f'{name}_scaled.csv'), index=False, encoding='utf-8')

    # 7. 补充统计信息（describe 给出每列均值/标准差/最值/分位数等）
    report['各列统计'] = df[FEATURE_COLS + TARGET_COLS].describe().round(4).to_dict()
    report['特征均值_标准化后'] = dict(zip(FEATURE_COLS, scaler.mean_.round(4)))    # scaler 学到的均值
    report['特征标准差_标准化后'] = dict(zip(FEATURE_COLS, scaler.scale_.round(4)))  # 学到的标准差

    # 8. 把完整预处理报告写成 JSON
    report_path = os.path.join(OUT_DIR, 'preprocess_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 控制台打印关键结果，方便运行时确认
    print('预处理完成。输出目录:', OUT_DIR)
    print(f'  全量样本: {len(df)}  |  训练: {len(train)}  |  验证: {len(val)}  |  测试: {len(test)}')
    print(f'  缺失值: {report["缺失值总数"]}  |  删除重复行: {report["删除重复行数"]}')
    print(f'  报告已保存: preprocess_report.json')


# 直接运行本脚本时执行 main；被 import 时不自动执行
if __name__ == '__main__':
    main()
