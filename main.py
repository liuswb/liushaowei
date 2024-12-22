from app import app

if __name__ == '__main__':
    # 设置主机名为 0.0.0.0 允许外部访问
    # 设置线程模式为 True 支持多线程
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) 