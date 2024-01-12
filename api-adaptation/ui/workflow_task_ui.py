import datetime
import json
import os.path
import re

import gradio as gr

from api.models import WorkflowVo
from db import WorkflowTaskTable
from service.workflow_service import WorkflowService


def show_task_status(status):
    return {
        "PENDING": "处理中", "FINISHED": "完成", "FAILED": "失败"
    }[status]


def get_task_data(query="", status=""):
    def row(task):
        return [
            task.task_id,
            f"{task.workflow_id}-{task.workflow_name}",
            show_task_status(task.task_status),
            f"{task.duration}s",
            task.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            task.tenant_id,
        ]

    tasks: list[WorkflowTaskTable] = WorkflowService().get_workflow_tasks(query, status)
    return [row(task) for task in tasks]


def show_task_result(workflow, task):
    if task.task_status == "FINISHED":
        return f"""
<img src="https://aigc-cos.rabbitpre.com/comfyui/preview_image/{task.task_id}.png" class="result-image" />
        """


def show_task_input(workflow, task):
    # 提取所有图片
    text = json.dumps(task.workflow_input_params, indent=4, ensure_ascii=False)
    images = re.findall(r"\"https?://\S+\"", text)
    text = ""
    for image in images:
        text += f"""
<img src={image} class="result-image" />
"""
    text = "\n无" if text == "" else text
    return text


def select_row(data_list, evt: gr.SelectData):
    task_id = data_list[evt.index[0]][0]
    tenant_id = data_list[evt.index[0]][5]
    task_vo = WorkflowService().get_workflow_task(tenant_id=tenant_id, task_id=task_id)
    workflow: WorkflowVo = WorkflowService().get_workflow(tenant_id=task_vo.tenant_id, workflow_id=task_vo.workflow_id)
    # 更新时间-创建时间，得到耗时
    return f"""
## 流程任务详情
- 任务Id `{task_vo.task_id}`
- 任务流程 `{task_vo.workflow_id}-{workflow.workflow_description}`
- comfyui节点 `{task_vo.comfyui_node_host}`
- comfyui返回的状态码 `{task_vo.status_code}`
- 流程入参
```javascript
{json.dumps(task_vo.workflow_input_params, indent=4, ensure_ascii=False)}
```
---
- 输入图片
{show_task_input(workflow, task_vo)}
- 输出图片 
{show_task_result(workflow, task_vo)}
"""


def render_ui():
    with gr.Blocks(title="Comfyui-流程任务", css=f"{os.path.dirname(__file__)}/ui.css") as demo:
        with gr.Row(variant="panel"):
            query_txt = gr.Textbox(show_label=False, lines=1, placeholder="任务ID/工作流ID/租户ID/工作流名称", scale=5,
                                   container=False)
            status_dropdown = gr.Dropdown(show_label=False,
                                          choices=[("处理中", "PENDING"), ("完成", "FINISHED"), ("失败", "FAILED")],
                                          scale=5, container=False)
            query_btn = gr.Button(value="查询", variant="primary", scale=2)
        with gr.Row():
            data_list = gr.Dataframe(headers=["任务ID", "流程", "状态", "耗时", "添加时间", "租户ID"],
                                     value=get_task_data, scale=3, interactive=False, row_count=100,
                                     type="array", elem_classes="my_table")
            with gr.Column(scale=2):
                markdown = gr.Markdown()

        data_list.select(select_row, inputs=[data_list], outputs=[markdown])

        query_btn.click(get_task_data, inputs=[query_txt, status_dropdown], outputs=[data_list])
    return demo


if __name__ == '__main__':
    render_ui().queue().launch()
