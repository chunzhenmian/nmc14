# -*- coding: utf-8 -*-
"""后端服务包：工业燃气轮机排放预测与运行参数智能优化系统。
本文件在 Python 把 backend 当作“包”导入时会自动执行一次。"""
import os
import sys

# 小知识：sys.path 是 Python 的“模块搜索路径清单”，import 时会按这个清单逐个文件夹找模块。
# 为了同时兼容下面两种启动方式（包内统一使用“以 backend 目录为根”的绝对导入）：
#   1) 进入 backend 目录直接运行：python app.py / python train_models.py
#      —— 此时 backend 目录本来就在 sys.path 中；
#   2) 在项目根以包方式导入：python -m backend.app、pytest（from app import ...）
#      —— 需要把 backend 目录显式加入 sys.path，保证 import config、
#         from api.routes import ... 等绝对导入在两种方式下都能找到模块。
# __file__ 是当前文件路径，abspath 取绝对路径，dirname 取所在文件夹，即 backend 目录
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:          # 已在清单里就不重复添加
    sys.path.insert(0, _BACKEND_DIR)      # insert(0,...) 放到最前面，优先搜索
