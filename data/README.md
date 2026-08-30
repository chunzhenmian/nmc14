# 数据来源说明

## 一、数据集基本信息

| 项目 | 内容 |
| :--- | :--- |
| 数据集名称 | Gas Turbine CO and NOx Emission Data Set（燃气轮机 CO 与 NOx 排放数据集） |
| 数据来源 | UCI Machine Learning Repository |
| 官方链接 | https://archive.ics.uci.edu/dataset/551/gas+turbine+co+and+nox+emission+data+set （**已验证有效，访问返回 HTTP 200**） |
| DOI | https://doi.org/10.24432/C5WC95 |
| 捐赠时间 | 2019-11-28 |
| 数据规模 | 36733 条小时级样本，11 个传感器测量值 |
| 缺失值 | 无缺失值 |
| 适用任务 | 回归（排放预测）、聚类（工况识别） |

> **引用方式**：Gas Turbine CO and NOx Emission Data Set [Dataset]. (2019). UCI Machine Learning Repository. https://doi.org/10.24432/C5WC95.

## 二、数据内容说明

数据采集自土耳其西北部某燃气轮机电站，覆盖 2011-01-01 至 2015-12-31 五年运行监测数据，按小时聚合。原始数据不含显式时间戳列，但**样本已按时间先后顺序排列**（本仓库预处理时按年份文件顺序拼接，保持时序顺序）。

### 字段含义表

| 字段 | 含义 | 单位 | 最小 | 最大 | 均值 | 角色 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| AT | 环境温度 Ambient temperature | °C | -6.23 | 37.10 | 17.71 | 特征 |
| AP | 环境压力 Ambient pressure | mbar | 985.85 | 1036.56 | 1013.07 | 特征 |
| AH | 环境湿度 Ambient humidity | % | 24.08 | 100.20 | 77.87 | 特征 |
| AFDP | 空气过滤器差压 Air filter difference pressure | mbar | 2.09 | 7.61 | 3.93 | 特征 |
| GTEP | 燃气轮机排气压力 Gas turbine exhaust pressure | mbar | 17.70 | 40.72 | 25.56 | 特征 |
| TIT | 涡轮进口温度 Turbine inlet temperature | °C | 1000.85 | 1100.89 | 1081.43 | 特征 |
| TAT | 涡轮排气温度 Turbine exhaust temperature | °C | 511.04 | 550.61 | 546.16 | 特征 |
| CDP | 压气机出口压力 Compressor discharge pressure | mbar | 9.85 | 15.16 | 12.06 | 特征 |
| TEY | 涡轮能量产出 Turbine energy yield | MWh | 100.02 | 179.50 | 133.51 | 特征/目标 |
| CO | 一氧化碳排放浓度 Carbon monoxide | mg/m³ | 0.00 | 44.10 | 2.37 | 目标 |
| NOX | 氮氧化物排放浓度 Nitrogen oxides | mg/m³ | 25.90 | 119.91 | 65.29 | 目标 |

> 说明：AT 存在 62 个负值样本，为冬季低温环境下的正常环境温度值，予以保留；数据经 UCI 官方声明无缺失值。

## 三、目录文件结构

```
data/
├── README.md            # 本说明文件（数据来源）
├── raw/                 # 原始数据（直接从 UCI 官方下载）
│   ├── gt_2011.csv      # 2011 年数据，7411 行
│   ├── gt_2012.csv      # 2012 年数据，7628 行
│   ├── gt_2013.csv      # 2013 年数据，7152 行
│   ├── gt_2014.csv      # 2014 年数据，7158 行
│   └── gt_2015.csv      # 2015 年数据，7384 行
└── processed/           # 预处理后数据（由 scripts/preprocess.py 生成）
```

## 四、数据获取方式

1. **本仓库已内置原始数据**：`data/raw/` 下 5 个年度 CSV 即官方原始数据文件，无需再下载。
2. **官方下载**：若需重新获取，可访问官方链接，或使用 Python 的 `ucimlrepo` 库：
   ```python
   from ucimlrepo import fetch_ucirepo
   data = fetch_ucirepo(id=551)  # 数据集编号 551
   ```

## 五、版权与使用说明

- 本数据集由 UCI Machine Learning Repository 公开发布，用于学术研究与教学用途。
- 本项目用于大三课程设计教学实践，仅作学习使用，不涉及商业用途。
- 使用时请按上述引用方式标注数据集出处。
