# -*- coding: utf-8 -*-
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import pytz
from datetime import datetime
from config import Config
from db.models import WorkflowTable, WorkflowTaskTable

# 设置全局时区为北京时间
pytz.timezone('Asia/Shanghai').localize(datetime.now())

# 在全局时区下获取当前时间
now = datetime.now()
print('当前时间:', now)

# 创建引擎
engine = create_engine(Config.db_connection_string, echo=True, pool_size=5, pool_recycle=60, max_overflow=5)
# 绑定引擎
DbSession = sessionmaker(bind=engine, autoflush=False)
# 创建数据库链接池，直接使用session即可为当前线程拿出一个链接对象conn
# 内部会采用threading.local进行隔离
# session = scoped_session(db_session)
# 创建线程本地数据对象
# thread_local = threading.local()

# 自动创建所有表
WorkflowTable.__table__.create(bind=engine, checkfirst=True)
WorkflowTaskTable.__table__.create(bind=engine, checkfirst=True)
