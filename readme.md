# 工业燃气轮机氮氧化物排放预测与运行参数智能优化系统

> 大三课程设计 · 智能制造工程专业
> 开发方法：vibe coding 开发方法 + Git 版本控制
> 技术架构：B/S 四层架构（前端 UI / 后端服务 / 数据库 / 算法模块）

## 一、项目简介

面向工业燃气轮机电站的运行优化与排放管控场景，构建完整 B/S 架构的可运行演示系统，实现三大核心功能：

1. **排放浓度精准预测** —— XGBoost 回归模型预测 NOx、CO 排放浓度与机组能量产出
2. **运行参数智能寻优** —— 粒子群优化算法（PSO）以排放达标为约束、最大化机组能量产出
3. **工况异常早期预警** —— 孤立森林算法识别偏离正常分布的工况异常与排放异常

## 二、系统架构

```
┌─────────────────────────────────────────────────────┐
│  前端 UI（Vue3 + Element Plus + ECharts）           │
│  运行总览 / 排放预测 / 参数优化 / 异常监测           │
└──────────────────────┬──────────────────────────────┘
                       │ RESTful API（axios，vite 代理）
┌──────────────────────▼──────────────────────────────┐
│  后端服务（Python Flask）                           │
│  业务服务层：排放等级判定、优化解析、预警分级        │
├─────────────────────────────────────────────────────┤
│  算法模块                                           │
│  ① XGBoost 排放预测   ② PSO 参数优化  ③ 孤立森林异常 │
├─────────────────────────────────────────────────────┤
│  数据库（MySQL 8.0 / 自动降级 SQLite）              │
│  device_basics / run_records / anomaly_logs         │
└─────────────────────────────────────────────────────┘
```

## 三、项目目录结构

```
大三课程设计/
├── readme.md               # 本文件（项目说明）
├── 选题说明.md              # 选题与目标说明
├── 方案设计.md              # 技术方案与架构设计
├── 学习笔记.md              # 课程学习笔记
├── docs/                   # 课程设计任务书等文档
├── data/                   # 数据目录
│   ├── README.md           # 数据来源说明
│   ├── raw/                # 原始数据（UCI 官方，5 个年度 CSV）
│   └── processed/          # 预处理后数据（训练/验证/测试集、scaler、报告）
├── scripts/                # 数据处理脚本
│   └── preprocess.py       # 数据预处理程序
├── backend/                # Flask 后端
│   ├── app.py              # 应用入口
│   ├── config.py           # 配置（特征/限值/参数边界/数据库）
│   ├── data_loader.py      # 数据加载器
│   ├── train_models.py     # 模型训练脚本
│   ├── models/             # 算法模块 + 训练产物
│   │   ├── predictor.py         # XGBoost 排放预测
│   │   ├── optimizer.py         # PSO 参数优化
│   │   ├── anomaly_detector.py  # 孤立森林异常检测
│   │   └── artifacts/           # 训练好的模型文件
│   ├── services/business.py # 业务服务层
│   ├── database/db.py       # 数据库访问层
│   ├── api/routes.py        # RESTful API 路由
│   ├── requirements.txt     # 依赖清单
│   └── tests/test_api.py    # 自动化测试（pytest）
└── frontend/               # Vue3 前端
    ├── package.json
    ├── vite.config.js       # 开发代理 /api → 5000
    └── src/
        ├── main.js / App.vue
        ├── router/index.js  # 路由
        ├── api/index.js     # axios 封装
        └── views/           # 四个业务页面
            ├── Overview.vue        # 运行总览
            ├── Prediction.vue      # 排放预测
            ├── Optimization.vue    # 参数优化
            └── AnomalyMonitor.vue  # 异常监测
```

## 四、快速运行

### 4.1 环境要求

- Python 3.9+（建议 3.10-3.13）
- Node.js 16+（建议 18+）
- MySQL 8.0（可选，未配置时自动降级 SQLite）

### 4.2 安装依赖

```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install
```

### 4.3 数据准备与模型训练

```bash
# 数据预处理（生成 data/processed/）
python scripts/preprocess.py

# 模型训练（生成 backend/models/artifacts/），两种方式等价
cd backend
python train_models.py        # 方式一：进入 backend 目录直接运行
# 方式二：在项目根以模块方式运行 python -m backend.train_models
```

> 仓库已内置预处理数据与训练好的模型，可直接运行系统，无需重复上述两步。

### 4.4 启动系统

**方式一（推荐，一键启动）**：Windows 下直接双击项目根目录的 **`一键启动.bat`**，会自动开两个窗口分别运行前后端，并在约 6 秒后自动打开浏览器；双击 **`一键停止.bat`** 可按端口停止前后端。脚本会在后端依赖或前端依赖缺失时自动安装。

**方式二（手动，分两个终端）**：

```bash
# 终端 1：启动后端（默认 http://127.0.0.1:5000）
cd backend
python app.py
# 也可在项目根以模块方式启动：python -m backend.app（两种方式均已适配）

# 终端 2：启动前端（默认 http://127.0.0.1:5173）
cd frontend && npm run dev
```

浏览器访问 **http://127.0.0.1:5173** 即可使用系统。

### 4.5 自动化测试

```bash
# 项目根运行
python -m pytest backend/tests -v
# 或进入 backend 目录运行：cd backend && python -m pytest tests -v
```

当前 **11 项测试全部通过**（健康检查、排放预测、参数优化、异常检测、记录查询）。

## 五、RESTful API 接口

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| GET | /api/health | 健康检查 |
| GET | /api/overview | 运行总览（设备/统计/最近记录） |
| POST | /api/predict | 排放预测（8 项运行参数 → TEY/CO/NOX + 等级） |
| POST | /api/optimize | 参数优化（PSO，可带基准参数对比） |
| POST | /api/anomaly/check | 工况异常检测（9 项特征 → 异常判定/预警等级） |
| GET | /api/records | 历史记录查询（?type=predict\|optimize） |
| GET | /api/anomalies | 异常预警日志 |
| GET | /api/device | 设备基础信息 |
| GET | /api/model/info | 模型评估信息 |

## 六、数据来源

使用 **UCI 燃气轮机 CO 与 NOx 排放数据集**：

- **官方链接**：https://archive.ics.uci.edu/dataset/551/gas+turbine+co+and+nox+emission+data+set （已验证有效，HTTP 200）
- **DOI**：https://doi.org/10.24432/C5WC95
- **规模**：土耳其某燃气电站 2011-2015 年连续运行监测数据，36733 条小时级样本，无缺失值

详见 [`data/README.md`](data/README.md)。

## 七、数据预处理

预处理程序 `scripts/preprocess.py`：合并 5 年数据 → 质量检查 → 去重（删 7 条重复）→ 按年份划分训练(2011-2013)/验证(2014)/测试(2015) → 特征标准化。产物位于 `data/processed/`。

**数据漂移说明**：经探查发现 NOX 存在跨年数据漂移（2011-2013 均值约 68-70 mg/m³，2014-2015 约 60），部署模型采用全量数据训练以兼顾实时预测场景，跨年外推影响已在 `backend/models/artifacts/train_report.json` 如实披露。

## 八、模型效果（验证集）

| 模型 | 用途 | R² | MAE | RMSE |
| :--- | :--- | :--- | :--- | :--- |
| XGBoost（8特征→TEY） | 能量产出预测 | 0.9986 | 0.43 | 0.59 |
| XGBoost（9特征→CO） | CO 排放预测 | 0.7942 | 0.50 | 0.99 |
| XGBoost（9特征→NOX） | NOX 排放预测 | 0.8634 | 2.80 | 4.22 |
| IsolationForest（9特征） | 工况异常检测 | — | — | — |

## 九、开发阶段进度

| 阶段 | 状态 | 说明 |
| :--- | :--- | :--- |
| 选题与方案设计 | ✅ 已完成 | 选题说明.md、方案设计.md |
| 数据准备 | ✅ 已完成 | 数据获取、预处理、prompt 追溯 |
| 模型开发 | ✅ 已完成 | 三算法模块训练与评估 |
| 后端开发 | ✅ 已完成 | Flask API + 数据库 + 自动化测试 |
| 前端开发 | ✅ 已完成 | Vue3 四页面 + 联调通过 |
| 集成调试与报告 | ⏳ 待开始 | 全流程测试、设计报告 |

## 十、vibe coding 开发档案（AI 工具提示词追溯）

与 AI 工具的交流记录统一归档至 [`prompt/`](prompt/) 目录，每个开发阶段同步更新，作为开发过程的可追溯档案。详见 [`prompt/README.md`](prompt/README.md)。
