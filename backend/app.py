# -*- coding: utf-8 -*-
"""
Flask 应用入口
==============
启动方式：
  python -m backend.app          # 开发模式，127.0.0.1:5000
  python backend/app.py
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS

from . import config
from .api.routes import api


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    app.register_blueprint(api)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({'error': '接口不存在'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': f'服务器内部错误: {e}'}), 500

    # 初始化数据库（失败不阻塞启动，自动降级 SQLite）
    try:
        from .database.db import get_db
        db = get_db()
        db.init_schema()
    except Exception as e:
        print(f'[app] 数据库初始化失败: {e}')

    return app


if __name__ == '__main__':
    app = create_app()
    print(f'* 后端服务启动: http://{config.HOST}:{config.PORT}')
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
