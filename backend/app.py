# -*- coding: utf-8 -*-
"""
=====================================================================
Flask 后端应用入口（app.py）
=====================================================================
这个文件是后端的“总入口 / 启动开关”，负责：
  1. 创建一个 Flask 网页服务（Flask 是 Python 的轻量后端框架）；
  2. 解决“跨域”问题，让 5173 端口的前端能调用 5000 端口的后端；
  3. 把写好的 9 个接口（蓝图 api）挂载到服务上；
  4. 程序一启动就准备好数据库；
  5. 定义统一的错误返回格式。

启动方式（推荐，直接运行不会报相对导入错误）：
  cd backend
  python app.py                  # 开发模式，访问 http://127.0.0.1:5000

在项目根也可用包方式启动：
  python -m backend.app
=====================================================================
"""
import os  # 操作系统工具（本文件实际较少直接用到，保留以备扩展）
from flask import Flask, jsonify          # Flask：创建后端服务；jsonify：把 Python 字典转成 JSON 返回给前端
from flask_cors import CORS               # CORS：跨域资源共享，允许不同端口的前端访问本后端

import config                             # 读取本目录下 config.py 里的全部配置
from api.routes import api               # api/routes.py 里定义的“蓝图”，9 个接口都打包在 api 里


def create_app():
    """【应用工厂函数】创建并配置好一个 Flask 应用对象后返回。
    用函数来“生产”app 的好处：测试时可以反复创建干净的服务实例。"""
    app = Flask(__name__)                 # 创建 Flask 应用，__name__ 告诉 Flask 当前模块位置
    app.config['SECRET_KEY'] = config.SECRET_KEY  # 写入密钥配置
    # 允许所有来源（*）对 /api/ 开头的接口跨域访问，否则浏览器会拦截前端发来的请求
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    # 把接口蓝图注册到应用上——注册后，routes.py 里写的 /api/health 等地址才真正生效
    app.register_blueprint(api)

    # 错误处理：当访问了不存在的接口地址时，自动返回统一的 JSON 提示和 404 状态码
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({'error': '接口不存在'}), 404

    # 错误处理：后端代码内部抛异常时，返回 500 状态码和错误信息，而不是直接崩给用户看
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': f'服务器内部错误: {e}'}), 500

    # 初始化数据库（失败不阻塞启动：MySQL 连不上时内部会自动降级到 SQLite）
    try:
        from database.db import get_db  # 导入“获取数据库连接”的函数（放在函数内导入，避免循环导入）
        db = get_db()                   # 拿到数据库单例对象
        db.init_schema()                # 建表 + 写入默认机组信息（表已存在则不会重复建）
    except Exception as e:
        # 即使数据库出问题也打印提示并继续启动，保证服务本身能跑起来
        print(f'[app] 数据库初始化失败: {e}')

    return app  # 把配置好的应用对象交出去


# __name__ == '__main__' 表示“本文件是被直接运行的”（而不是被别的文件 import）
# 只有直接 python app.py 时才执行下面的启动代码；被测试导入时不会重复启动服务
if __name__ == '__main__':
    app = create_app()  # 创建应用
    print(f'* 后端服务启动: http://{config.HOST}:{config.PORT}')  # 打印访问地址
    # 启动 Flask 自带的开发服务器，按 config 里的地址、端口、调试模式运行
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
