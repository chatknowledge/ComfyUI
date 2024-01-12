import time

from sqlalchemy import or_, and_

from api.models import WorkflowVo, PromptRequest, WorkflowGetJsonRequest
from config import Config
from db import DbSession
from db.models import WorkflowTable, WorkflowTaskTable
from service.cos_service import CosService
from service.error_defind import WorkflowNoFoundError


class WorkflowService:
    def __init__(self):
        self.cos = CosService()
        self.image_cos = CosService(Config.image_cos_config)

    def get_workflows(self, tenant_id: int = None) -> list[WorkflowVo]:
        """
        获取工作流列表
        """
        with DbSession() as session:
            if tenant_id:
                workflows_table = session.query(WorkflowTable).order_by(WorkflowTable.workflow_id) \
                    .filter(WorkflowTable.tenant_id.in_([-1, tenant_id]),
                            WorkflowTable.workflow_status == "RELEASED").all()

            else:
                workflows_table = session.query(WorkflowTable).order_by(WorkflowTable.workflow_id).all()
            return [WorkflowVo(**workflow.to_dict()) for workflow in workflows_table]

    def get_workflow(self, tenant_id, workflow_id) -> WorkflowVo:
        """获取工作流"""
        with DbSession() as session:
            workflow_table = session.query(WorkflowTable).filter(
                WorkflowTable.workflow_id == workflow_id,
                WorkflowTable.tenant_id.in_([-1, tenant_id]),
                WorkflowTable.is_delete == 0,
            ).first()
            assert workflow_table, WorkflowNoFoundError(f"工作流不存在: {workflow_id}")
            vo = WorkflowVo(**workflow_table.to_dict())
            vo._request_cos_key = workflow_table.workflow_api_key
            vo._workflow_cos_key = workflow_table.workflow_key
            vo._workflow_input_mapping = workflow_table.workflow_input_mapping
            vo._workflow_out_mapping = workflow_table.workflow_out_mapping
            vo._workflow_befor_scripts = workflow_table.workflow_befor_scripts
        return vo

    def get_workflow_task(self, tenant_id, task_id) -> WorkflowTaskTable:
        """获取工作流任务"""
        with DbSession() as session:
            workflow_task = session.query(WorkflowTaskTable).filter(
                WorkflowTaskTable.task_id == task_id,
                WorkflowTable.tenant_id.in_([-1, tenant_id]),
                WorkflowTaskTable.is_delete == 0,
            ).first()
        return workflow_task

    def add_workflow_task(self, request: PromptRequest, comfyui_node_host, workflow: WorkflowVo, status_code, text,
                          start_time, prompt_id: str, task_status: str, task_result="生成中"):
        """
        保存工作流任务
        :param prompt_id:
        :param start_time:
        :param request: 请求
        :param comfyui_node_host: comfyui节点
        :param workflow: WorkflowVo
        :param status_code: comfyui返回的状态码
        :param text: comfyui返回的结果
        :param task_status:
        :param task_result:
        :return:
        """
        table = WorkflowTaskTable()
        table.task_id = request.request_id
        table.workflow_id = request.workflow_id
        table.tenant_id = request.tenant_id
        table.workflow_name = workflow.workflow_name
        table.workflow_input_params = request.workflow_params
        table.workflow_output_params = workflow.workflow_output_params
        table.workflow_input_mapping = workflow.workflow_input_mapping
        table.workflow_out_mapping = workflow.workflow_out_mapping
        table.comfyui_node_host = comfyui_node_host
        table.status_code = status_code
        table.text = text
        table.is_sync = request.is_sync
        table.duration = int((time.time() - start_time) * 1000)
        table.prompt_id = prompt_id
        table.task_status = task_status
        table.task_result = task_result
        with DbSession() as session:
            session.merge(table)
            session.commit()
            session.flush()
        return table

    def update_workflow_task(self, workflow_task_table: WorkflowTaskTable):
        with DbSession() as session:
            session.merge(workflow_task_table)
            session.commit()
            session.flush()

    def get_workflow_json(self, request: WorkflowGetJsonRequest):
        """获取工作流配置"""
        try:
            get_workflow = self.get_workflow(request.tenant_id, request.workflow_id)
            return self.cos.get_workflow_json(get_workflow.workflow_cos_key)
        except Exception as e:
            raise WorkflowNoFoundError(f"工作流不存在: {request.workflow_id}")

    def get_workflow_tasks(self, query, status="") -> list[WorkflowTaskTable]:
        """获取工作流任务列表"""
        filters_like = []
        filters_and = []
        if query:
            filters_like.append(WorkflowTaskTable.task_id.like(f"%{query}%"))
            filters_like.append(WorkflowTaskTable.workflow_name.like(f"%{query}%"))
            filters_like.append(WorkflowTaskTable.workflow_id.like(f"%{query}%"))
            filters_like.append(WorkflowTaskTable.tenant_id.like(f"%{query}%"))
        if status:
            filters_and.append(WorkflowTaskTable.task_status == status)
        with DbSession() as session:
            workflow_task = session.query(WorkflowTaskTable).order_by(WorkflowTaskTable.create_time.desc()).filter(
                or_(*filters_like), and_(*filters_and)).limit(500)
        for task in workflow_task:
            task.duration = round((task.update_time - task.create_time).total_seconds(), 2)
        return workflow_task
