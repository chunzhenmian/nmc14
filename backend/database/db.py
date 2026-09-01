# -*- coding: utf-8 -*-
"""
数据库访问层
============
支持两种后端：
  - MySQL（默认，需配置 DB_USER/DB_PASSWORD 等环境变量或 config.DB_CONFIG）
  - SQLite（当 MySQL 连接失败时自动降级，保证系统可演示）

三张业务表：
  1. device_basics  设备基础信息（额定参数、排放标准）
  2. run_records    运行与优化记录（排放预测、参数优化方案）
  3. anomaly_logs   异常监测日志
"""
import os
import json
import sqlite3
from datetime import datetime

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS device_basics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name VARCHAR(128),
    rated_power_mw REAL,
    design_tit_c REAL,
    noise_limit_nox REAL,
    noise_limit_co REAL,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS run_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type VARCHAR(32),
    params_json TEXT,
    result_json TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS anomaly_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    params_json TEXT,
    score REAL,
    level VARCHAR(32),
    description TEXT,
    created_at TEXT
);
"""


class Database:
    """统一数据库接口：MySQL 优先，失败降级 SQLite"""

    def __init__(self, cfg=None):
        self.cfg = cfg or config.DB_CONFIG
        self.conn = None
        self.backend = None
        self._connect()

    # ---------- 连接 ----------
    def _connect(self):
        if self.cfg.get('type') == 'mysql':
            try:
                import pymysql
                self.conn = pymysql.connect(
                    host=self.cfg['host'], port=self.cfg['port'],
                    user=self.cfg['user'], password=self.cfg['password'],
                    database=self.cfg['database'], charset='utf8mb4',
                    autocommit=True, connect_timeout=3,
                )
                self.backend = 'mysql'
                print(f'[db] 已连接 MySQL: {self.cfg["host"]}:{self.cfg["port"]}/{self.cfg["database"]}')
            except Exception as e:
                print(f'[db] MySQL 连接失败({e})，降级使用 SQLite')
                self._connect_sqlite()
        else:
            self._connect_sqlite()

    def _connect_sqlite(self):
        os.makedirs(os.path.dirname(self.cfg['sqlite_path']), exist_ok=True)
        self.conn = sqlite3.connect(self.cfg['sqlite_path'], check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.backend = 'sqlite'
        print(f'[db] 已连接 SQLite: {self.cfg["sqlite_path"]}')

    def init_schema(self):
        """初始化表结构并写入设备基础数据"""
        cur = self.conn.cursor()
        # MySQL 需要确保数据库存在
        if self.backend == 'mysql':
            self._ensure_database()
        cur.executescript(SCHEMA)
        self.conn.commit()
        self._seed_device()
        print(f'[db] 表结构初始化完成 (backend={self.backend})')

    def _ensure_database(self):
        """MySQL 下若数据库不存在则创建"""
        import pymysql
        try:
            conn = pymysql.connect(host=self.cfg['host'], port=self.cfg['port'],
                                   user=self.cfg['user'], password=self.cfg['password'],
                                   charset='utf8mb4', autocommit=True, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.cfg['database']}` "
                    f"DEFAULT CHARACTER SET utf8mb4")
            conn.close()
            # 重新连接目标库
            self.conn.close()
            self.conn = pymysql.connect(
                host=self.cfg['host'], port=self.cfg['port'],
                user=self.cfg['user'], password=self.cfg['password'],
                database=self.cfg['database'], charset='utf8mb4',
                autocommit=True, connect_timeout=3)
        except Exception as e:
            print(f'[db] 创建 MySQL 数据库失败({e})，继续使用当前连接')

    def _seed_device(self):
        """写入默认设备基础信息（不存在时）"""
        d = config.DEVICE_BASICS
        cur = self.conn.cursor()
        cnt = cur.execute('SELECT COUNT(*) FROM device_basics').fetchone()
        if (cnt[0] if isinstance(cnt, tuple) else int(cnt[0])) == 0:
            cur.execute(
                'INSERT INTO device_basics (device_name, rated_power_mw, design_tit_c, '
                'noise_limit_nox, noise_limit_co, created_at) VALUES (?,?,?,?,?,?)',
                (d['device_name'], d['rated_power_mw'], d['design_tit_c'],
                 d['noise_limit_nox'], d['noise_limit_co'],
                 datetime.now().isoformat(timespec='seconds')))
            self.conn.commit()

    # ---------- 通用执行 ----------
    def execute(self, sql, args=None):
        cur = self.conn.cursor()
        cur.execute(sql, args or ())
        self.conn.commit()
        return cur

    def fetch(self, sql, args=None):
        cur = self.conn.cursor()
        cur.execute(sql, args or ())
        rows = cur.fetchall()
        if self.backend == 'mysql':
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    # ---------- 记录管理 ----------
    def add_run_record(self, record_type, params, result):
        sql = ('INSERT INTO run_records (record_type, params_json, result_json, created_at) '
               'VALUES (?,?,?,?)')
        self.execute(sql, (record_type, json.dumps(params, ensure_ascii=False),
                           json.dumps(result, ensure_ascii=False),
                           datetime.now().isoformat(timespec='seconds')))

    def add_anomaly_log(self, params, score, level, description):
        sql = ('INSERT INTO anomaly_logs (params_json, score, level, description, created_at) '
               'VALUES (?,?,?,?,?)')
        self.execute(sql, (json.dumps(params, ensure_ascii=False), score, level,
                           description, datetime.now().isoformat(timespec='seconds')))

    def get_records(self, record_type=None, limit=50):
        sql = 'SELECT * FROM run_records'
        args = []
        if record_type:
            sql += ' WHERE record_type = ?'
            args.append(record_type)
        sql += ' ORDER BY id DESC LIMIT ?'
        args.append(limit)
        rows = self.fetch(sql, args)
        for r in rows:
            try:
                r['params'] = json.loads(r.pop('params_json'))
                r['result'] = json.loads(r.pop('result_json'))
            except (json.JSONDecodeError, KeyError):
                pass
        return rows

    def get_anomaly_logs(self, limit=50):
        rows = self.fetch(
            'SELECT * FROM anomaly_logs ORDER BY id DESC LIMIT ?', (limit,))
        for r in rows:
            try:
                r['params'] = json.loads(r.pop('params_json'))
            except (json.JSONDecodeError, KeyError):
                pass
        return rows

    def get_device_basics(self):
        rows = self.fetch('SELECT * FROM device_basics ORDER BY id LIMIT 1')
        return rows[0] if rows else None

    def stats(self):
        """汇总统计（总览页用）"""
        def _count(sql):
            r = self.fetch(sql)
            v = r[0] if r else {}
            return int(list(v.values())[0]) if v else 0
        return {
            'predict_records': _count("SELECT COUNT(*) AS c FROM run_records WHERE record_type='predict'"),
            'optimize_records': _count("SELECT COUNT(*) AS c FROM run_records WHERE record_type='optimize'"),
            'anomaly_records': _count('SELECT COUNT(*) AS c FROM anomaly_logs'),
            'anomaly_high': _count("SELECT COUNT(*) AS c FROM anomaly_logs WHERE level IN ('红色预警','橙色预警')"),
        }


_db = None


def get_db():
    """全局单例数据库"""
    global _db
    if _db is None:
        _db = Database()
    return _db


def close_db():
    global _db
    if _db is not None:
        try:
            _db.conn.close()
        except Exception:
            pass
        _db = None
