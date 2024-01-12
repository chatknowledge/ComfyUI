# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer, JSON, Text
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class BaseTable(Base):
    __abstract__ = True
    create_time: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.now)
    update_time: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    is_delete = Column(Integer, default=0, comment="是否已删除")

    def to_dict(self):
        data = self.__dict__
        return data


class WorkflowTable(BaseTable):
    __tablename__ = "t_workflow"
    workflow_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment='流程ID', autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, comment='租户ID')
    workflow_name: Mapped[str] = mapped_column(String(100), comment='流程名称')
    workflow_description: Mapped[str] = mapped_column(String(200), comment='流程描述')
    agent_type: Mapped[str] = mapped_column(String(200), comment='agent类型 TEXT、IMAGE、FIND_IMAGE')
    workflow_input_params: Mapped[str] = mapped_column(JSON, comment='流程入参')
    workflow_output_params: Mapped[str] = mapped_column(JSON, comment='流程回参')
    workflow_input_mapping: Mapped[str] = mapped_column(JSON, comment='流程入参映射')
    workflow_out_mapping: Mapped[str] = mapped_column(JSON, comment='流程出参映射')
    workflow_status: Mapped[str] = mapped_column(String(100), comment='流程状态：RELEASED:已发布，UNRELEASED：未发布')
    workflow_api_key: Mapped[str] = mapped_column(String(100), comment='流程配置API的key')
    workflow_key: Mapped[str] = mapped_column(String(100), comment='流程配置的key')
    workflow_befor_scripts: Mapped[str] = mapped_column(String(200), comment='流程Scripts，针对一些特殊流程，多个用,拼接')
    workflow_after_scripts: Mapped[str] = mapped_column(String(200), comment='流程Scripts，针对一些特殊流程，多个用,拼接')


class WorkflowTaskTable(BaseTable):
    __tablename__ = "t_workflow_task"
    task_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment='流程任务ID')
    workflow_id: Mapped[str] = mapped_column(String(50), comment='流程ID')
    tenant_id: Mapped[int] = mapped_column(Integer, comment='租户ID')
    workflow_name: Mapped[str] = mapped_column(String(100), comment='流程名称')
    workflow_input_params: Mapped[str] = mapped_column(JSON, comment='流程入参')
    workflow_output_params: Mapped[str] = mapped_column(JSON, comment='流程回参')
    workflow_input_mapping: Mapped[str] = mapped_column(JSON, comment='流程入参映射')
    workflow_out_mapping: Mapped[str] = mapped_column(JSON, comment='流程出参映射')
    comfyui_node_host: Mapped[str] = mapped_column(String(100), comment='comfyui节点')
    status_code: Mapped[int] = mapped_column(Integer, comment='comfyui返回的状态码')
    text: Mapped[str] = mapped_column(Text, comment='comfyui返回的结果')
    prompt_id: Mapped[str] = mapped_column(String(50), comment='comfyui返回的prompt_id')
    is_sync: Mapped[bool] = mapped_column(Integer, comment='是否同步')
    duration: Mapped[int] = mapped_column(Integer, comment='花费毫秒')
    task_status: Mapped[str] = mapped_column(String(20),
                                             comment='状态：PENDING:生成中，FINISHED：生成成功，FAILED：生成失败')
    task_result: Mapped[str] = mapped_column(String(200), comment='结果')
