# -*- coding: utf-8 -*-
"""
后端配置模块
"""
import os

# ---------- 路径 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_PROCESSED = os.path.join(PROJECT_ROOT, 'data', 'processed')
MODEL_DIR = os.path.join(BASE_DIR, 'models', 'artifacts')
os.makedirs(MODEL_DIR, exist_ok=True)

# ---------- 特征与目标列 ----------
# 8 项可调节/可观测运行参数（不含能量产出，用于 TEY 预测与参数优化）
FEATURES_8 = ['AT', 'AP', 'AH', 'AFDP', 'GTEP', 'TIT', 'TAT', 'CDP']
# 9 项特征（含 TEY，用于 CO/NOX 排放预测）
FEATURES_9 = FEATURES_8 + ['TEY']
TARGET_COLS = ['CO', 'NOX']

# ---------- 运行参数合理区间（PSO 优化搜索边界，取自数据分位数并外扩） ----------
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

# ---------- 排放达标阈值（mg/m³，示例标准，可在业务层调整） ----------
EMISSION_LIMITS = {
    'CO':  30.0,    # 一氧化碳排放限值
    'NOX': 100.0,   # 氮氧化物排放限值
}

# ---------- 数据库配置（默认 MySQL，可通过环境变量覆盖；连接失败自动降级 SQLite） ----------
DB_CONFIG = {
    'type': os.getenv('DB_TYPE', 'mysql'),          # mysql / sqlite
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'gt_emission_system'),
    'sqlite_path': os.path.join(BASE_DIR, 'data', 'system.db'),
}

# ---------- Flask ----------
SECRET_KEY = os.getenv('SECRET_KEY', 'gt-emission-course-design')
DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
HOST = os.getenv('FLASK_HOST', '127.0.0.1')
PORT = int(os.getenv('FLASK_PORT', 5000))

# ---------- 设备额定参数（数据库初始化种子数据） ----------
DEVICE_BASICS = {
    'device_name': '工业燃气轮机机组 GT-01',
    'rated_power_mw': 180.0,
    'design_tit_c': 1100.0,
    'noise_limit_nox': EMISSION_LIMITS['NOX'],
    'noise_limit_co': EMISSION_LIMITS['CO'],
}
