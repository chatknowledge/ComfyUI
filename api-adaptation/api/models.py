from json import JSONEncoder

from datetime import datetime
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Any, Union

from config import Config


class TaskStatus:
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class CustomJsonEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, BaseModel):
            return obj.__dict__
        return super().default(obj)


class ResponseBase(BaseModel):
    """提问回参"""
    code: int = Field(0, title='状态码', description="0表示成功，其他为失败")
    message: str = Field("成功", title='消息')
    data: Any = Field(None, title='数据')
    request_id: str = Field("", title="请求id", description="流水号")


def toResponse(code: int = 0, message: str = "成功", data: Any = None, request_id: str = ""):
    return Response(
        content=CustomJsonEncoder(ensure_ascii=False, sort_keys=True, indent=4).encode({
            "code": code,
            "message": message,
            "data": data,
            "request_id": request_id
        }),
        media_type='application/json; charset=UTF-8'
    )


class PromptRequest(BaseModel):
    """提问入参"""
    request_id: str = Field(None, title='流水号', description="可为空")
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")
    workflow_id: int = Field(..., title="工作流id")
    workflow_params: Any = Field(None,
                                 title="工作流参数(动态字段)",
                                 description="参考：===> <a href='/workflow-docs'>/workflow/docs</a>")
    is_sync: bool = Field(False, title="是否同步")


class HistoryRequest(BaseModel):
    """推理结果查询入参"""
    task_id: str = Field(..., title='任务ID', description="同推理的request_id")
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")


class WorkflowRequest(BaseModel):
    """删除入参"""
    request_id: str = Field(None, title='流水号', description="可为空")
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")
    workflow_id: str = Field(..., title="工作流id")


class WorkflowVo(BaseModel):
    """Workflow对象"""
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")
    workflow_id: int = Field(..., title="工作流id")
    workflow_name: str = Field(..., title="工作流名称")
    agent_type: str = Field(..., title="agent类型 TEXT、IMAGE、FIND_IMAGE")
    workflow_description: str = Field(None, title="工作流描述")
    workflow_input_params: list[dict] = Field(None, title="流程入参")
    workflow_output_params: list[dict] = Field(None, title="流程回参")
    create_time: datetime = Field(None, title="添加时间")
    update_time: datetime = Field(None, title="更新时间")
    is_delete: int = Field(0, title="是否删除")

    # 不会返回给前端,也不会接口文档中显示
    _request_cos_key: str
    _workflow_cos_key: str
    _workflow_input_mapping: dict
    _workflow_out_mapping: dict
    _workflow_befor_scripts: str
    _workflow_after_scripts: str

    @property
    def workflow_cos_key(self):
        return self._workflow_cos_key

    @property
    def request_cos_key(self):
        return self._request_cos_key

    @property
    def workflow_input_mapping(self):
        return self._workflow_input_mapping

    @property
    def workflow_out_mapping(self):
        return self._workflow_out_mapping

    @property
    def workflow_befor_scripts(self):
        return self._workflow_befor_scripts

    @property
    def workflow_after_scripts(self):
        return self._workflow_after_scripts


class ResponseWorkflows(BaseModel):
    """Workflow配置列表回参"""
    request_id: str = Field("", title="请求id", description="流水号")
    code: int = Field(0, title='状态码', description="0表示成功，其他为失败")
    message: str = Field("成功", title='消息')
    data: list[WorkflowVo] = Field(None, title='Workflow配置列表')


class ResponseWorkflow(BaseModel):
    """Workflow配置列表回参"""
    request_id: str = Field("", title="请求id", description="流水号")
    code: int = Field(0, title='状态码', description="0表示成功，其他为失败")
    message: str = Field("成功", title='消息')
    data: list[WorkflowVo] = Field(None, title='Workflow配置列表')


class WorkflowListRequest(BaseModel):
    """请求工作流列表入参"""
    request_id: str = Field(None, title='流水号', description="可为空")
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")


class WorkflowGetJsonRequest(BaseModel):
    """请求工作流配置入参"""
    tenant_id: int = Field(Config.default_tenant_id, title='租户id', description="可为空")
    workflow_id: int = Field(..., title="工作流id")
