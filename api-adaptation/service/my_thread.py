import threading


# 定义一个线程类
class MyThread(threading.Thread):
    def __init__(self, target, args=()):
        super(MyThread, self).__init__()
        self.target = target
        self.args = args
        self.result = None

    def run(self):
        try:
            self.result = self.target(*self.args)
        except Exception as e:
            self.result = e


