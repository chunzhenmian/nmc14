# -*- coding: utf-8 -*-
"""
=====================================================================
数据库访问层（db.py）
=====================================================================
【这个文件做什么】
统一封装所有“存数据、取数据”的操作，上层业务不用关心底层到底用的是哪种数据库。

支持两种数据库后端（自动选择）：
  · MySQL：正式的数据库服务，默认优先尝试（需要本机装了 MySQL 并配好账号密码）；
  · SQLite：免安装的“单文件数据库”，整个库就是一个 system.db 文件。
    一旦 MySQL 连不上，代码会自动改用 SQLite，保证在任何电脑上都能直接演示。

一共三张业务表：
  1. device_basics  设备基础信息（额定参数、排放标准），一般只有 1 行
  2. run_records    运行记录（每次“排放预测 / 参数优化”存一行）
  3. anomaly_logs   异常监测日志（每次异常检测存一行）

小知识：SQL 里的 ? 是“参数占位符”，实际值由数据库安全填入，可防止 SQL 注入。
=====================================================================
"""
import os
import json                 # 字典和 JSON 字符串互转（数据库文本字段里存 JSON）
import sqlite3              # Python 自带的 SQLite 驱动，无需额外安装
from datetime import datetime  # 生成时间戳

import config

# 建表脚本（三张小表）。IF NOT EXISTS 表示“表不存在才创建”，重复执行不会报错或清空数据
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
    """统一数据库接口：优先连 MySQL，失败自动降级到 SQLite，对上暴露同一套方法。"""

    def __init__(self, cfg=None):
        self.cfg = cfg or config.DB_CONFIG  # 不传配置就用 config 里的数据库配置
        self.conn = None                    # 数据库连接对象，稍后建立
        self.backend = None                 # 记录当前实际用的是 'mysql' 还是 'sqlite'
        self._connect()                     # 创建对象时立即连接

    # ---------- 连接 ----------
    def _connect(self):
        """根据配置选择数据库：配置成 mysql 就先试 MySQL，失败或配置成其它就走 SQLite。"""
        if self.cfg.get('type') == 'mysql':
            try:
                import pymysql              # pymysql：Python 连接 MySQL 的库（用到时才导入）
                self.conn = pymysql.connect(
                    host=self.cfg['host'], port=self.cfg['port'],
                    user=self.cfg['user'], password=self.cfg['password'],
                    database=self.cfg['database'], charset='utf8mb4',
                    autocommit=True, connect_timeout=3,  # 3秒连不上就判定失败，快速降级
                )
                self.backend = 'mysql'
                print(f'[db] 已连接 MySQL: {self.cfg["host"]}:{self.cfg["port"]}/{self.cfg["database"]}')
            except Exception as e:
                # MySQL 没装/账号密码不对等任何原因失败，都不崩溃，改连 SQLite
                print(f'[db] MySQL 连接失败({e})，降级使用 SQLite')
                self._connect_sqlite()
        else:
            self._connect_sqlite()

    def _connect_sqlite(self):
        """连接（必要时创建）SQLite 文件数据库。"""
        # 确保存放 system.db 的 data 文件夹存在
        os.makedirs(os.path.dirname(self.cfg['sqlite_path']), exist_ok=True)
        # check_same_thread=False：允许 Flask 多线程请求共用同一连接
        self.conn = sqlite3.connect(self.cfg['sqlite_path'], check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 让查询结果能按“列名”取值（像字典）
        self.backend = 'sqlite'
        print(f'[db] 已连接 SQLite: {self.cfg["sqlite_path"]}')

    def init_schema(self):
        """初始化：执行建表脚本，并写入一条默认设备档案。应用启动时调用一次。"""
        cur = self.conn.cursor()             # 游标：用来执行 SQL 的对象
        # MySQL 需要先保证“数据库”本身存在
        if self.backend == 'mysql':
            self._ensure_database()
        cur.executescript(SCHEMA)            # executescript：一次执行多条建表语句
        self.conn.commit()                   # 提交，使改动真正落库
        self._seed_device()                  # 写入默认机组信息
        print(f'[db] 表结构初始化完成 (backend={self.backend})')

    def _ensure_database(self):
        """仅 MySQL 用：若目标数据库还不存在就先创建，然后重新连到该库。"""
        import pymysql
        try:
            # 先不指定 database 连接到 MySQL 服务
            conn = pymysql.connect(host=self.cfg['host'], port=self.cfg['port'],
                                   user=self.cfg['user'], password=self.cfg['password'],
                                   charset='utf8mb4', autocommit=True, connect_timeout=3)
            with conn.cursor() as cur:
                # CREATE DATABASE IF NOT EXISTS：库不存在才建；反引号包裹库名
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.cfg['database']}` "
                    f"DEFAULT CHARACTER SET utf8mb4")
            conn.close()
            # 关掉旧连接，重新连接到刚确保存在的目标数据库
            self.conn.close()
            self.conn = pymysql.connect(
                host=self.cfg['host'], port=self.cfg['port'],
                user=self.cfg['user'], password=self.cfg['password'],
                database=self.cfg['database'], charset='utf8mb4',
                autocommit=True, connect_timeout=3)
        except Exception as e:
            print(f'[db] 创建 MySQL 数据库失败({e})，继续使用当前连接')

    def _seed_device(self):
        """设备表为空时，写入 config 里的默认机组信息（只播一次“种子数据”）。"""
        d = config.DEVICE_BASICS
        cur = self.conn.cursor()
        cnt = cur.execute('SELECT COUNT(*) FROM device_basics').fetchone()  # 统计行数
        # 不同数据库返回计数的形式略有差异，下面这行做兼容，最终拿到整数行数
        if (cnt[0] if isinstance(cnt, tuple) else int(cnt[0])) == 0:
            cur.execute(
                'INSERT INTO device_basics (device_name, rated_power_mw, design_tit_c, '
                'noise_limit_nox, noise_limit_co, created_at) VALUES (?,?,?,?,?,?)',
                (d['device_name'], d['rated_power_mw'], d['design_tit_c'],
                 d['noise_limit_nox'], d['noise_limit_co'],
                 datetime.now().isoformat(timespec='seconds')))  # isoformat 生成标准格式时间字符串
            self.conn.commit()

    # ---------- 通用执行 ----------
    def execute(self, sql, args=None):
        """执行“写操作”（增/删/改）：args 是填进 ? 占位符的参数元组。"""
        cur = self.conn.cursor()
        cur.execute(sql, args or ())   # args 为 None 时用空元组
        self.conn.commit()             # 写操作需要提交
        return cur

    def fetch(self, sql, args=None):
        """执行“读操作”（查）：返回由字典组成的列表，每个字典是一行。"""
        cur = self.conn.cursor()
        cur.execute(sql, args or ())
        rows = cur.fetchall()          # fetchall：取出全部查询结果
        # 把每一行统一转成 {列名: 值} 的字典，MySQL/SQLite 表现一致
        if self.backend == 'mysql':
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    # ---------- 记录管理 ----------
    def add_run_record(self, record_type, params, result):
        """新增一条运行/优化记录。params、result 是字典，用 json.dumps 转成文本存储
        （ensure_ascii=False 保证中文不被转成 \\u 编码，可读性更好）。"""
        sql = ('INSERT INTO run_records (record_type, params_json, result_json, created_at) '
               'VALUES (?,?,?,?)')
        self.execute(sql, (record_type, json.dumps(params, ensure_ascii=False),
                           json.dumps(result, ensure_ascii=False),
                           datetime.now().isoformat(timespec='seconds')))

    def add_anomaly_log(self, params, score, level, description):
        """新增一条异常检测日志。"""
        sql = ('INSERT INTO anomaly_logs (params_json, score, level, description, created_at) '
               'VALUES (?,?,?,?,?)')
        self.execute(sql, (json.dumps(params, ensure_ascii=False), score, level,
                           description, datetime.now().isoformat(timespec='seconds')))

    def get_records(self, record_type=None, limit=50):
        """查询运行记录，可按类型筛选；按 id 倒序（最新在前），最多返回 limit 条。"""
        sql = 'SELECT * FROM run_records'
        args = []
        if record_type:                       # 传了类型才拼接 WHERE 条件，避免写死
            sql += ' WHERE record_type = ?'
            args.append(record_type)
        sql += ' ORDER BY id DESC LIMIT ?'    # 倒序 + 限量
        args.append(limit)
        rows = self.fetch(sql, args)
        for r in rows:
            try:
                # 把存进去的 JSON 文本重新解析成字典，并改名为 params/result 方便前端使用
                r['params'] = json.loads(r.pop('params_json'))
                r['result'] = json.loads(r.pop('result_json'))
            except (json.JSONDecodeError, KeyError):
                pass                          # 个别老数据解析失败就跳过，不影响整体
        return rows

    def get_anomaly_logs(self, limit=50):
        """查询异常日志（最新在前），同样把 params_json 解析回字典。"""
        rows = self.fetch(
            'SELECT * FROM anomaly_logs ORDER BY id DESC LIMIT ?', (limit,))
        for r in rows:
            try:
                r['params'] = json.loads(r.pop('params_json'))
            except (json.JSONDecodeError, KeyError):
                pass
        return rows

    def get_device_basics(self):
        """取设备档案（只有一条，取最早的 id 即可）；没有则返回 None。"""
        rows = self.fetch('SELECT * FROM device_basics ORDER BY id LIMIT 1')
        return rows[0] if rows else None

    def stats(self):
        """首页用的汇总统计：分别数出预测、优化、异常记录条数，以及橙/红色预警条数。"""
        def _count(sql):
            # 内部小函数：执行一条 COUNT 查询并返回整数
            r = self.fetch(sql)
            v = r[0] if r else {}
            return int(list(v.values())[0]) if v else 0
        return {
            'predict_records': _count("SELECT COUNT(*) AS c FROM run_records WHERE record_type='predict'"),
            'optimize_records': _count("SELECT COUNT(*) AS c FROM run_records WHERE record_type='optimize'"),
            'anomaly_records': _count('SELECT COUNT(*) AS c FROM anomaly_logs'),
            'anomaly_high': _count("SELECT COUNT(*) AS c FROM anomaly_logs WHERE level IN ('红色预警','橙色预警')"),
        }


# 模块级变量，保存全局唯一的数据库实例（单例）
_db = None


def get_db():
    """【单例模式】整个程序共用一个数据库连接：第一次调用时创建，之后直接复用。
    global 声明：函数内要修改模块级变量 _db，必须用 global 声明。"""
    global _db
    if _db is None:
        _db = Database()
    return _db


def close_db():
    """关闭数据库连接并把单例清空（一般在程序退出或测试清理时用）。"""
    global _db
    if _db is not None:
        try:
            _db.conn.close()
        except Exception:
            pass        # 关闭时即使报错也忽略，保证能把 _db 重置
        _db = None
