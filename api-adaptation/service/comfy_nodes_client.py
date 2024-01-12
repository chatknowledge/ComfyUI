import base64
import importlib
import json
import os.path
import time
import uuid
from io import BytesIO

import requests
from db_hammer.util.array_util import cut_list_data
from db_hammer.util.file import get_dir_files
from jsonpath_ng.ext import parse
from loguru import logger
from retry import retry

from api.models import WorkflowVo, PromptRequest, HistoryRequest, TaskStatus
from config import Config
from db import WorkflowTaskTable
from service.cos_service import CosService
from service.error_defind import ComfyInvokeError, ComfyParamError, ComfyParameterizationError, WorkflowTaskExistError, \
    WorkflowTaskNoFoundError, ComfyuiViewImageError, ComfyuiTaksWaitError
from service.my_thread import MyThread
from service.workflow_service import WorkflowService


class ComfyNodesClient:
    """ComfyUI的节点调用客户端"""

    def __init__(self):
        self.nodes = Config.comfyui_node_hosts.split(",")
        self.model_node_map = {}
        self.node_index = 0
        self.cos = CosService()
        self.image_cos = CosService(Config.image_cos_config)
        self.workflow_service = WorkflowService()

    def select_node(self, request_json) -> str:
        """
        选择节点, 根据模型动态切换节点
        """
        ckpt_name = None
        expression = parse("$..ckpt_name")
        matches = [match for match in expression.find(json.loads(request_json))]
        if matches:
            ckpt_name = matches[0].value
        if ckpt_name and ckpt_name in self.model_node_map:
            node = self.model_node_map.get(ckpt_name)
            logger.info(f"select comfyui ref node: {node}")
            return node
        # 兜底
        if self.node_index >= len(self.nodes):
            self.node_index = 0
        node = str(self.nodes[self.node_index]).strip()
        logger.info(f"select comfyui new node: {node}")
        self.model_node_map[ckpt_name] = node
        self.node_index += 1
        return node

    def invoke_prompt(self, request: PromptRequest) -> dict:
        """
        调用ComfyUI的prompt接口
        :param request: 请求
        :return:
        """
        start_time = time.time()
        # 流水号唯一
        assert not self.workflow_service.get_workflow_task(request.tenant_id,
                                                           request.request_id), WorkflowTaskExistError()
        # 1. 获取到工作流的配置
        workflow = self.workflow_service.get_workflow(request.tenant_id, request.workflow_id)

        # 1.1 增加前处理脚本
        if workflow.workflow_befor_scripts:
            for script in workflow.workflow_befor_scripts.split(","):
                logger.info(f"[{request.request_id}]-执行前处理脚本: {script}")
                script = importlib.import_module("scripts." + script)
                script.run(request)

        # 2. 从cos中获取到工作流的配置
        request_json = self.cos.get_workflow_api_json(workflow.request_cos_key)
        comfyui_node_host = self.select_node(request_json)
        # 3. 参数化
        request_json = self.input_parameterization(request.request_id, workflow, request_json, request.workflow_params,
                                                   comfyui_node_host)

        # 4. 调用ComfyUI的prompt接口
        url = f'{comfyui_node_host}/prompt'
        logger.debug(f"[{request.request_id}]-调用ComfyUI {url}的prompt接口参数: {request_json}")
        response = requests.post(url, json=request_json)
        logger.info(f"[{request.request_id}]-调用ComfyUI的prompt接口结果: {response.text}")
        if response.status_code == 200:
            prompt_id = response.json().get("prompt_id")
        else:
            prompt_id = ""
        # 5. 入库到数据库
        task_status = TaskStatus.PENDING
        workflow_task = self.workflow_service.add_workflow_task(request, comfyui_node_host,
                                                                workflow, response.status_code,
                                                                response.text, start_time, prompt_id,
                                                                task_status=task_status)
        assert response.status_code == 200, ComfyInvokeError(f"调用ComfyUI的prompt接口失败: {response.text}")
        # 6. 另开一个线程等待结果
        try:
            output = self.get_task_result(workflow_task)
            if request.is_sync:
                task_status = TaskStatus.FINISHED
        except Exception as e:
            logger.exception(e)
            task_status = TaskStatus.FAILED
            output = {}

        return {
            "task_id": request.request_id,
            "task_status": task_status,
            **output
        }

    def input_parameterization(self, request_id, workflow: WorkflowVo, request_json, workflow_input_params,
                               comfyui_node_host):
        """
        参数化
        :param request_id: 请求id
        :param workflow: 工作流配置
        :param request_json: 请求json
        :param workflow_input_params: 请求参数
        :param comfyui_node_host: comfyui节点
        :return:
        """
        try:
            request_obj = json.loads(request_json)
            # 1. 处理数据库中的参数映射
            for param in workflow.workflow_input_params:
                logger.info(
                    f"[{request_id}]-请求参数化: {param}")
                # 1.1. 替换参数
                param_name = param.get("name", "")
                required = param.get("required", False)
                default = param.get("default_value", None)
                _type = param.get("type", None)
                rule_type = param.get("rule_type", "")
                if required and param_name not in workflow_input_params:
                    logger.warning(f"[{request_id}]-缺少必要参数【{param_name}】请检查你的接口请求参数")
                    raise ComfyParamError(f"缺少必要参数【{param_name}】请检查你的接口请求参数")

                if param_name not in workflow.workflow_input_mapping:
                    logger.warning(f"[{request_id}]-出现额外参数【{param}】，流程配置的mapping缺少参数【{param_name}】")
                    raise ComfyParamError(
                        f"[{request_id}]-出现额外参数【{param}】，流程配置的mapping缺少参数【{param_name}】")
                expression = parse(workflow.workflow_input_mapping[param_name])
                logger.info(
                    f"[{request_id}]-参数化目标表达式: {expression}")
                matches = [match for match in expression.find(request_obj)]
                if matches:
                    # 替换所有
                    if param_name in workflow_input_params:
                        value = workflow_input_params[param_name]
                        # 类型转换
                        if _type == "str" and rule_type in ["IMAGE", "VIEW_FINDER"]:
                            value = self.upload_image(confy_node_host=comfyui_node_host,
                                                      image_url=value)
                    else:
                        value = default
                    if _type == "seed" and str(value) in ("-1", "0"):
                        # 使用当前时间作为种子。这样可以保证每次生成的种子都是不同的。
                        value = int(time.time() * 10)
                        logger.debug("seed random value: {}", value)
                    logger.info("seed value: {}", value)

                    logger.info(f"[{request_id}]-参数化目标value: {value}")
                    expression.update(request_obj, value)
                else:
                    logger.warning(f"[{request_id}]-参数【{param}】的流程配置问题，请联系配置人员")
                    raise ComfyParamError(f"参数【{param}】的流程配置问题，请联系配置人员")
                logger.info(f"[{request_id}]-参数化完成")

            return {
                "client_id": request_id,
                "prompt": request_obj,
            }
        except ComfyParameterizationError as e:
            logger.error(f"[{request_id}]-参数化失败: {e}")
            raise ComfyParameterizationError(f"参数化失败: {e}")

    def invoke_history(self, request: HistoryRequest):
        """
        调用历史接口
        :param request:
        :return:
        """
        workflow_task = self.workflow_service.get_workflow_task(request.tenant_id, request.task_id)
        assert workflow_task, WorkflowTaskNoFoundError()
        if workflow_task.task_status == TaskStatus.FINISHED:
            return {
                "task_id": request.task_id,
                "task_status": workflow_task.task_status,
                **self.output_parameterization(workflow_task, json.loads(workflow_task.text))
            }
        else:
            return {
                "task_id": request.task_id,
                "task_status": workflow_task.task_status,
            }
        # raise ComfyInvokeError(f"调用ComfyUI的history接口失败")

    @retry(exceptions=ComfyuiTaksWaitError, tries=300, delay=1, backoff=1)
    def invoke_history_api(self, workflow_task):
        url = f'{workflow_task.comfyui_node_host}/history/{workflow_task.prompt_id}'
        logger.info(f"[{workflow_task.task_id}]-请求历史接口: {url}")
        response = requests.get(url)
        logger.info(f"[{workflow_task.task_id}]-调用ComfyUI的history接口结果: {response.text}")
        assert response.status_code == 200, ComfyInvokeError(f"调用ComfyUI的history接口失败: {response.text}")
        data = response.json()
        if len(data):
            workflow_task.task_status = TaskStatus.FINISHED
            workflow_task.text = json.dumps(list(data.values())[0])
            return self.output_parameterization(workflow_task, list(data.values())[0])
        else:
            workflow_task.task_status = TaskStatus.PENDING
            raise ComfyuiTaksWaitError()

    def retry_invoke_history_api(self, workflow_task):
        try:
            res = self.invoke_history_api(workflow_task)
            workflow_task.task_result = "成功"
            return res
        except ComfyuiTaksWaitError as e:
            workflow_task.task_status = TaskStatus.FAILED
            workflow_task.task_result = "生成超时"
        except Exception as e:
            logger.exception(e)
            workflow_task.task_status = TaskStatus.FAILED
            workflow_task.task_result = "生成异常:" + str(e)
        finally:
            self.workflow_service.update_workflow_task(workflow_task)

    def get_task_result(self, workflow_task: WorkflowTaskTable) -> dict:
        """
        任务结果
        :param workflow_task:
        :return:
        """
        if not workflow_task.is_sync:
            thread = MyThread(target=self.retry_invoke_history_api, args=(workflow_task,))
            thread.start()
        else:
            return self.retry_invoke_history_api(workflow_task)
        return {}

    def output_parameterization(self, workflow_task, data) -> dict:
        """
        出参参数化
        :param workflow_task:
        :param data:
        :return:
        """
        logger.debug(f"[{workflow_task.task_id}]-出参参数化: {data}")
        workflow = self.workflow_service.get_workflow(workflow_task.tenant_id, workflow_task.workflow_id)
        result = {}
        try:
            for param in workflow.workflow_output_params:
                name = param.get("name", "")
                _type = param.get("type", None)
                if name in workflow.workflow_out_mapping:
                    expression = parse(workflow.workflow_out_mapping[name])
                    logger.debug(f"[{workflow_task.task_id}]-参数化目标表达式: {expression}")
                    matches = [match for match in expression.find(data)]
                    if matches:
                        out_image = matches[0].value
                        image_body = self.get_preview_image(confy_node_host=workflow_task.comfyui_node_host,
                                                            file_type=out_image["type"],
                                                            filename=out_image["filename"])
                        # 类型转换
                        if _type == "int":
                            result[name] = int(matches[0].value)
                        elif _type == "float":
                            result[name] = float(matches[0].value)
                        elif _type == "base64":
                            result[name] = base64.b64encode(image_body).decode("utf-8")

                        elif _type == "url":
                            filename = f"preview_image/{workflow_task.task_id}.png"
                            result[name] = self.image_cos.upload(
                                filename=filename,
                                body=image_body)
                        else:
                            result[name] = matches[0].value

        except Exception as e:
            logger.exception(e)
            raise ComfyParameterizationError(f"出参参数化失败: {e}")
        return result

    def get_preview_image(self, confy_node_host, file_type, filename):
        preview_url = f"{confy_node_host}/view?filename={filename}&subfolder=&type={file_type}&rand={time.time()}"
        response = requests.get(preview_url)
        assert response.status_code == 200, ComfyuiViewImageError()
        return response.content

    @retry(exceptions=Exception, tries=3, delay=0, backoff=0)
    def upload_image(self, confy_node_host, image_url):
        url = f"{confy_node_host}/upload/image"
        logger.info("上传图片到ComfyUI: {} ", image_url)
        image_res = requests.get(image_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        assert image_res.status_code == 200, ComfyuiViewImageError(f"下载图片失败：{image_url} {image_res.status_code} ")
        filename = os.path.basename(image_url)
        files = {"image": (
            str(uuid.uuid4()) + "_" + filename, BytesIO(image_res.content),
            image_res.headers.get("Content-Type", "image/png"))}
        response = requests.post(url, files=files)
        logger.info("上传图片到ComfyUI结果: {} {} ", response.status_code, response.text)
        assert response.status_code == 200, ComfyuiViewImageError()
        return response.json().get("name")
