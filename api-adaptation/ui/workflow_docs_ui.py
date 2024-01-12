import json
import os
import uuid

import gradio as gr
from loguru import logger

from api.models import WorkflowVo
from config import Config
from service.workflow_service import WorkflowService
import ui.workflow_test_ui as test_ui


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
        text += f'''        "{param['name']}": "{param['default_value']}",\n'''

    return text[:-2]


def get_input_params_value(params, key, ctype="text", group=None):
    for param in params:
        if param["name"] in key:
            if ctype == "number":
                value = float(param["default_value"])
            else:
                value = param["default_value"]
            if group:
                return gr.update(visible=True, value=value), gr.update(visible=True)
            else:
                return gr.update(visible=True, value=value)

    if group:
        return gr.update(visible=False, value=None), gr.update(visible=False)
    else:
        return gr.update(visible=False, value=None)


def get_api_markdown(workflow_id: str = "10001"):
    workflow = WorkflowService().get_workflow(tenant_id=-1, workflow_id=workflow_id)
    markdown = deal_markdown(workflow)
    return (markdown,
            workflow.workflow_id,
            *get_input_params_value(workflow.workflow_input_params, ["positive_prompt"], "text", True),
            *get_input_params_value(workflow.workflow_input_params, ["negative_prompt"], "text", True),
            get_input_params_value(workflow.workflow_input_params, ["similarity"], "number", False),
            get_input_params_value(workflow.workflow_input_params, ["image_base"], "image", False),
            get_input_params_value(workflow.workflow_input_params, ["image_style"], "image", False),
            input_json(workflow),
            get_input_params_value(workflow.workflow_input_params, ["seed"], "number", False))


def input_json(workflow):
    return f"""
{{
"workflow_id": {workflow.workflow_id},
"workflow_params": {{
{get_input_params_json(workflow)}
}},
"is_sync": true
}}
"""


def deal_markdown(workflow):
    markdown = f"""
## {workflow.workflow_description}
流程ID:`{workflow.workflow_id}`
流程名称:`{workflow.workflow_name}`
流程描述:`{workflow.workflow_description}`

<a href="/?workflow_id={workflow.workflow_id}">预览流程</a>

#### 入参：

| 参数名|  标题 |  类型 |   必填 |   默认值 |  
|  ----  | ----  | ----  | ----  | ----  |
{get_input_params(workflow)}

*请求参数示例：*
```javascript
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

*CURL示例：*
```shell
curl --location --request POST '{Config.docs_host}/prompt' \
--header 'Content-Type: application/json' \
--data-raw '{{
"request_id": "{uuid.uuid4()}",
"tenant_id": -1,
"workflow_id": {workflow.workflow_id},
"workflow_params": {{
{get_input_params_json(workflow)}
}},
"is_sync": true
}}'
```


#### 出参：

|  参数名   | 标题  | 类型 |
|  ----  | ----  | ----  |
{get_output_params(workflow)}

    """
    return markdown


def get_index_list_value():
    workflows = WorkflowService().get_workflows()
    choices = [(f"{workflow.workflow_id}-{workflow.workflow_description}", workflow.workflow_id) for workflow in
               workflows]
    return choices, choices[0][1]


choices, value = get_index_list_value()


def resfersh():
    choices, value = get_index_list_value()
    return gr.update(choices=choices, value=value)


def render_ui():
    with gr.Blocks(title="Comfyui-流程接口", css=f"{os.path.dirname(__file__)}/ui.css") as demo:
        with gr.Row():
            with gr.Column(scale=2, variant="panel"):
                resfersh_btn = gr.Button(value="刷新", variant="primary")
                index_radio = gr.Radio(label="流程列表", choices=choices, elem_id="index_list")
            with gr.Column(scale=10, variant="panel", elem_classes="tab_end"):
                with gr.Tab("接口文档"):
                    doc_mk = gr.Markdown(value="请选择流程", elem_classes="my_table")
                with gr.Tab("接口测试"):
                    test_demo = test_ui.render_ui()

        resfersh_btn.click(resfersh, outputs=index_radio)
        index_radio.change(get_api_markdown, inputs=[index_radio],
                           outputs=[doc_mk, test_demo.workflow_id, *test_demo.test_inputs])

    return demo


if __name__ == '__main__':
    render_ui().queue().launch()
