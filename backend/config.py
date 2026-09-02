# -*- coding: utf-8 -*-
"""
=====================================================================
后端配置模块（config.py）
=====================================================================
这个文件相当于整个后端的“总设置 / 总开关”：
  · 数据文件、训练好的模型放在哪个文件夹；
  · 用哪些列作为模型输入、预测哪些目标；
  · 每个可调参数允许的取值范围；
  · 排放标准是多少；
  · 数据库怎么连、后端服务跑在哪个地址端口。

其它所有 .py 文件需要这些设置时，都会 `import config` 后来这里取，
这样“设置”和“业务逻辑”分开，以后想改阈值、改端口，只改本文件即可。
=====================================================================
"""
import os  # os 是 Python 自带的“操作系统工具”，这里主要用来拼文件路径、读环境变量

# ---------- 路径 ----------
# __file__ 指当前这个 config.py 文件本身；abspath 取它的绝对路径；dirname 取所在文件夹
# 所以 BASE_DIR 就是后端文件夹 backend 的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 再往上退一层，就是整个项目的根目录（backend 的上一级）
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# 预处理后的数据目录：项目根目录 / data / processed
DATA_PROCESSED = os.path.join(PROJECT_ROOT, 'data', 'processed')
# 训练好的模型保存目录：backend / models / artifacts
MODEL_DIR = os.path.join(BASE_DIR, 'models', 'artifacts')
# 如果模型目录还不存在就自动创建（exist_ok=True 表示已存在也不报错）
os.makedirs(MODEL_DIR, exist_ok=True)

# ---------- 特征与目标列 ----------
# “特征”就是喂给模型的输入；“目标”就是模型要预测的结果
# 8 项可调节/可观测运行参数（不含能量产出 TEY，用于第一步预测 TEY，以及 PSO 参数优化）
# AT 环境温度、AP 环境压力、AH 环境湿度、AFDP 过滤器差压、GTEP 排气压力、
# TIT 涡轮进口温度、TAT 涡轮排气温度、CDP 压气机出口压力
FEATURES_8 = ['AT', 'AP', 'AH', 'AFDP', 'GTEP', 'TIT', 'TAT', 'CDP']
# 9 项特征 = 上面 8 项 + TEY 能量产出；第二步预测 CO/NOX 时，把第一步预测出的 TEY 也作为输入
FEATURES_9 = FEATURES_8 + ['TEY']
# 模型最终要预测的两个排放目标：CO 一氧化碳、NOX 氮氧化物
TARGET_COLS = ['CO', 'NOX']

# ---------- 运行参数合理区间（PSO 优化时的搜索边界，取自数据分位数并适当外扩） ----------
# 格式：参数名: (最小值, 最大值)。PSO 寻优时只会在这个“盒子”内找最优参数，不会给出离谱的值
PARAM_BOUNDS = {
    'AT':   (-8.0, 40.0),     # 环境温度 °C
    'AP':   (980.0, 1040.0),  # 环境压力 mbar
    'AH':   (20.0, 102.0),    # 环境湿度 %
    'AFDP': (1.5, 9.0),       # 空气过滤器差压 mbar
    'GTEP': (15.0, 45.0),     # 燃气轮机排气压力 mbar
    'TIT':  (990.0, 1110.0),  # 涡轮进口温度 °C
    'TAT':  (500.0, 560.0),   # 涡轮排气温度 °C
    'CDP':  (9.0, 17.0),      # 压气机出口压力 mbar
}

# ---------- 排放达标阈值（单位 mg/m³，示例标准，可按需调整） ----------
# 预测值超过对应数值即视为“超标”，PSO 优化时会对超标方案施加惩罚
EMISSION_LIMITS = {
    'CO':  30.0,    # 一氧化碳排放限值
    'NOX': 100.0,   # 氮氧化物排放限值
}

# ---------- 数据库配置 ----------
# 设计思路：默认尝试连 MySQL，连不上就自动降级到免安装的 SQLite 文件库，保证任何电脑都能跑起来
# os.getenv('名字', 默认值)：先看系统环境变量里有没有设置，没有就用默认值。这样不改代码也能切换配置
DB_CONFIG = {
    'type': os.getenv('DB_TYPE', 'mysql'),          # 数据库类型：mysql 或 sqlite
    'host': os.getenv('DB_HOST', '127.0.0.1'),      # 数据库服务器地址（本机）
    'port': int(os.getenv('DB_PORT', 3306)),        # MySQL 默认端口 3306，int() 把字符串转成整数
    'user': os.getenv('DB_USER', 'root'),           # 数据库用户名
    'password': os.getenv('DB_PASSWORD', ''),       # 数据库密码（默认空）
    'database': os.getenv('DB_NAME', 'gt_emission_system'),  # 数据库名
    'sqlite_path': os.path.join(BASE_DIR, 'data', 'system.db'),  # 降级时用的 SQLite 文件路径
}

# ---------- Flask 后端服务配置 ----------
SECRET_KEY = os.getenv('SECRET_KEY', 'gt-emission-course-design')  # Flask 用的密钥（本课程项目用默认值即可）
DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'  # 是否开启调试模式：环境变量等于字符串'1'时为 True
HOST = os.getenv('FLASK_HOST', '127.0.0.1')   # 监听地址，127.0.0.1 表示只允许本机访问
PORT = int(os.getenv('FLASK_PORT', 5000))     # 后端端口 5000（前端会把 /api 请求代理到这里）

# ---------- 设备额定参数（数据库第一次启动时写入的“种子数据”，相当于示例机组档案） ----------
DEVICE_BASICS = {
    'device_name': '工业燃气轮机机组 GT-01',  # 机组名称
    'rated_power_mw': 180.0,                  # 额定功率 180 兆瓦
    'design_tit_c': 1100.0,                   # 设计涡轮进口温度
    'noise_limit_nox': EMISSION_LIMITS['NOX'],  # NOX 排放限值（引用上面的配置，避免重复写）
    'noise_limit_co': EMISSION_LIMITS['CO'],     # CO 排放限值
}
