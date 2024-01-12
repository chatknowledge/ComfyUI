import json
import os.path
from datetime import datetime

import gradio as gr

from api.models import WorkflowVo
from db import DbSession, WorkflowTable
from service.cos_service import CosService
from service.workflow_service import WorkflowService


def get_input_params(workflow: WorkflowVo):
    text = ""
    for param in workflow.workflow_input_params:
        text += f"| {param['name']}  | {param['title']} | {param['type']} | {param['required']} | {param['default_value']} |\n"
    return text


def get_output_params(workflow: WorkflowVo):
    text = ""
    for param in workflow.workflow_output_params:
        text += f"| {param['name']}  | {param['title']} | {param['type']} |\n"
    return text


def get_input_params_json(workflow: WorkflowVo):
    text = ""
    for param in workflow.workflow_input_params:
        text += f'''        "{param['name']}": "{param['default_value']},\n'''

    return text[:-2]


def get_api_markdown():
    workflows = WorkflowService().get_workflows()
    markdown = f"# Comfyui-流程接口(总计：{len(workflows)}个):\n"
    for workflow in workflows:
        markdown += f"""
## <span style='color:brown'>{workflow.workflow_id}--{workflow.workflow_name}</span>
> {workflow.workflow_description}

<a href="/?workflow_id={workflow.workflow_id}">预览流程</a>

### 入参：

| 参数名|  标题 |  类型 |   必填 |   默认值 |  
|  ----  | ----  | ----  | ----  | ----  |
{get_input_params(workflow)}

JSON格式示例：
```json
{{
    "request_id": "{{% mock 'uuid' %}}",
    "tenant_id": -1,
    "workflow_id": {workflow.workflow_id},
    "workflow_params": {{
{get_input_params_json(workflow)}
    }},
    "is_sync": true
}}
```


### 出参：

|  参数名   | 标题  | 类型 |
|  ----  | ----  | ----  |
{get_output_params(workflow)}

---
        """
    return markdown


def render_ui():
    with gr.Blocks(title="Comfyui-配置后台", css=f"{os.path.dirname(__file__)}/ui.css") as demo:
        with gr.Row():
            with gr.Row():
                workflow_id = gr.Text(label="workflow_id", scale=4)
                workflow_id_query = gr.Button(value="查询", min_width=40)
            tenant_id = gr.Text(label="tenant_id", value="-1")
            workflow_name = gr.Text(label="workflow_name")
            workflow_description = gr.Text(label="workflow_description")
        with gr.Row():
            gr.Markdown("""
                #### 字段说明：
                * rule_type: NOTE 文本，IMAGE 图片，VIEW_FINDER 取景框，DEFAULT 前端默认
                * type: str 字符串，int 整数，float 浮点数，bool 布尔值，url 链接, seed 随机种子（0，-1）代表随机
                * required: true 必填，false 非必填
                * default_value: 默认值
                """)
        with gr.Row():
            workflow_input_params = gr.Code(label="workflow_input_params", language="json", interactive=True)
            workflow_output_params = gr.Code(label="workflow_output_params", interactive=True, language="json")
        with gr.Row():
            workflow_input_mapping = gr.Code(label="workflow_input_mapping", interactive=True, language="json")
            workflow_output_mapping = gr.Code(label="workflow_output_mapping", interactive=True, language="json")
        with gr.Row():
            workflow_config_json = gr.File(label="流程文件", type="binary")
            workflow_api_json = gr.File(label="API文件", type="binary")

        gr.Button(value="保存流程", variant="primary").click(save_workflow,
                                                             inputs=[workflow_id, tenant_id,
                                                                     workflow_name,
                                                                     workflow_description,
                                                                     workflow_input_params,
                                                                     workflow_output_mapping,
                                                                     workflow_output_params,
                                                                     workflow_input_mapping,
                                                                     workflow_config_json,
                                                                     workflow_api_json])
        workflow_id_query.click(query_workflow, inputs=[workflow_id],
                                outputs=[tenant_id,
                                         workflow_name,
                                         workflow_description,
                                         workflow_input_params,
                                         workflow_output_mapping,
                                         workflow_output_params,
                                         workflow_input_mapping,
                                         workflow_config_json,
                                         workflow_api_json
                                         ])
    return demo


def save_workflow(workflow_id, tenant_id,
                  workflow_name,
                  workflow_description,
                  workflow_input_params,
                  workflow_output_mapping,
                  workflow_output_params,
                  workflow_input_mapping,
                  workflow_config_json,
                  workflow_api_json):
    try:
        cos = CosService()
        with DbSession() as session:
            workflow_table: WorkflowTable = session.query(WorkflowTable).filter(
                WorkflowTable.workflow_id == workflow_id,
                WorkflowTable.is_delete == 0,
            ).first()
            if not workflow_table:
                workflow_table = WorkflowTable()
            workflow_table.workflow_id = workflow_id
            workflow_table.workflow_name = workflow_name
            workflow_table.workflow_description = workflow_description
            workflow_table.workflow_input_params = json.loads(workflow_input_params)
            workflow_table.workflow_output_params = json.loads(workflow_output_params)
            workflow_table.workflow_out_mapping = json.loads(workflow_output_mapping)
            workflow_table.workflow_input_mapping = json.loads(workflow_input_mapping)
            if workflow_config_json:
                workflow_table.workflow_key = cos.upload_config(
                    filename=f"workflows/{tenant_id}/{workflow_name}_workflow.json",
                    body=workflow_config_json)
            if workflow_api_json:
                workflow_table.workflow_api_key = cos.upload_config(
                    filename=f"workflows/{tenant_id}/{workflow_name}_workflow_api.json",
                    body=workflow_api_json)
            workflow_table.tenant_id = tenant_id
            workflow_table.is_delete = 0
            workflow_table.workflow_status = "RELEASED"
            workflow_table.agent_type = "IMAGE"
            workflow_table.create_time = datetime.now()
            workflow_table.update_time = datetime.now()
            session.merge(workflow_table)
            session.commit()
            session.flush()
            gr.Info("保存成功")
    except Exception as e:
        raise gr.Error(str(e))


def query_workflow(workflow_id):
    with DbSession() as session:
        workflow_table: WorkflowTable = session.query(WorkflowTable).filter(
            WorkflowTable.workflow_id == workflow_id,
            WorkflowTable.is_delete == 0,
        ).first()
        if not workflow_table:
            raise gr.Error("流程不存在")
        return workflow_table.tenant_id, \
            workflow_table.workflow_name, \
            workflow_table.workflow_description, \
            json.dumps(workflow_table.workflow_input_params, indent=2, ensure_ascii=False), \
            json.dumps(workflow_table.workflow_out_mapping, indent=2, ensure_ascii=False), \
            json.dumps(workflow_table.workflow_output_params, indent=2, ensure_ascii=False), \
            json.dumps(workflow_table.workflow_input_mapping, indent=2, ensure_ascii=False), None, None


if __name__ == '__main__':
    render_ui().queue().launch()
