import json
import time
import uuid

import fastapi
import uvicorn
from fastapi import FastAPI
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from api.models import *
from config import Config
from service.comfy_nodes_client import ComfyNodesClient
from service.error_defind import ComfyParamError
from service.workflow_service import WorkflowService
from ui.workflow_admin_ui import mount_workflow_admin

app = FastAPI(title="ComfyUI-Api-Adaptation",
              version="v0.1",
              description="""
### 查看已配置的流程接口文档 ===> <a href="/workflow-docs">/workflow/docs</a>
              """)
mount_workflow_admin(app)
workflow_service = WorkflowService()
comfyNodes_client = ComfyNodesClient()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源的请求
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    allow_credentials=True,  # 允许发送凭据（如cookie）
    expose_headers=["Content-Disposition"]  # 允许暴露的响应头
)


@app.get("/", include_in_schema=False)
async def index():
    return "ComfyUI-Api-Adaptation"


@app.on_event("startup")
async def startup_event():
    logger.info("-------api启动-------")


@app.middleware("http")
async def check_token(request: fastapi.Request, call_next):
    path = request.url.path
    client_ip = request.client.host
    start_time = time.time()
    logger.info(f"----------请求接口：{path}----client_ip:{client_ip}------")
    response: JSONResponse = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{path} 接口时间：{round(process_time, 2)} s")
    logger.info(f"---------------------------------------")
    return response


@app.post("/prompt", summary='请求推理',
          response_model=ResponseBase, tags=["推理"])
def prompt(prompt_request: PromptRequest):
    logger.info(f"===>请求推理：{json.dumps(prompt_request.__dict__, ensure_ascii=False)})")
    if not prompt_request.request_id:
        prompt_request.request_id = str(uuid.uuid4())
        # 处理动态参数
    try:
        if isinstance(prompt_request.workflow_params, str):
            prompt_request.workflow_params = json.loads(prompt_request.workflow_params)
    except Exception as e:
        logger.error(f"workflow_params参数格式错误：{e}")
        raise ComfyParamError("workflow_params参数格式错误")

    output = comfyNodes_client.invoke_prompt(prompt_request)
    logger.info(f"===>请求推理结果：{CustomJsonEncoder().encode(output)}")
    return toResponse(request_id=prompt_request.request_id, data=output, message="请求成功")


@app.post("/history", summary='推理结果查询',
          response_model=ResponseBase, tags=["推理"])
def history(history_request: HistoryRequest):
    logger.info(f"===>推理结果查询：{json.dumps(history_request.__dict__, ensure_ascii=False)})")

    output = comfyNodes_client.invoke_history(history_request)
    logger.info(f"===>推理结果查询结果：{CustomJsonEncoder().encode(output)}")
    response = toResponse(request_id=history_request.task_id, data=output, message="请求成功")
    return response


@app.post("/workflow/delete", summary='工作流删除',
          response_model=ResponseBase, tags=["工作流"])
def workflow_delete(workflow_request: WorkflowRequest):
    return "ComfyUI-Api-Adaptation"


@app.post("/workflow/get", summary='工作流获取',
          response_model=ResponseWorkflow, tags=["工作流"])
def workflow_get(workflow_request: WorkflowRequest):
    return "ComfyUI-Api-Adaptation"


@app.post("/workflow/list", summary='工作流列表',
          response_model=ResponseWorkflows, tags=["工作流"])
def workflow_list(request: fastapi.Request, workflow_list_request: WorkflowListRequest):
    logger.info(f"===>工作流列表：{json.dumps(workflow_list_request.__dict__, ensure_ascii=False)})")
    output = workflow_service.get_workflows(workflow_list_request.tenant_id)
    logger.info(f"===>工作流列表结果：{CustomJsonEncoder().encode(output)}")
    response = toResponse(request_id=workflow_list_request.request_id,
                          data=output)
    return response


@app.post("/workflow/get_json", summary='获取工作流配置',
          response_model=ResponseBase, tags=["工作流"])
def workflow_get_json(workflow_get_json_request: WorkflowGetJsonRequest):
    logger.info(f"===>获取工作流配置：{json.dumps(workflow_get_json_request.__dict__, ensure_ascii=False)})")
    data = workflow_service.get_workflow_json(workflow_get_json_request)
    response = toResponse(data=data)
    logger.info(f"===>获取工作流配置结果：{CustomJsonEncoder().encode(data)}")
    return response


# noinspection PyUnresolvedReferences
@app.exception_handler(Exception)
async def exception_handler(request: fastapi.Request, exc: Exception):
    message = "服务内部错误"
    code = 500
    if hasattr(exc, "Code"):
        message = str(exc) if str(exc) else exc.__doc__
        code = exc.Code
    if isinstance(exc, AssertionError) and hasattr(exc.args[0], "Code"):
        message = str(exc.args[0]) if str(exc.args[0]) else exc.args[0].__doc__
        code = exc.args[0].Code
    if code == 500:
        logger.exception(exc)

    logger.info(f"===>异常结果：{message}")
    return toResponse(code=code, message=message)


def run():
    uvicorn.run("api.fastapp:app", host="0.0.0.0", port=Config.api_port, log_level="info")
