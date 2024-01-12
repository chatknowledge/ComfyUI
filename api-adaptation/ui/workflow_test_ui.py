import io
import json
import os
import time
import uuid

import gradio as gr
import requests
from loguru import logger

from api.models import WorkflowVo, PromptRequest
from config import Config
from service.cos_service import CosService
import scripts.prompt_chat_befor as prompt_chat_befor

cos = CosService(Config.image_cos_config)


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


def reset(similarity):
    return gr.update(value=["1234"] * similarity)


def run_api(workflow_id, positive_prompt, negative_prompt, similarity, image_base, image_style, seed):
    try:
        assert workflow_id, gr.Warning("请先选择工作流")
        task_id = "TEST-" + str(time.time()).replace(".", "")
        data = {
            "request_id": task_id,
            "workflow_id": workflow_id,
            "workflow_params": {
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "similarity": similarity,
                "image_base": image_base,
                "image_style": image_style,
                "seed": seed,
            },
            "is_sync": True
        }
        if image_base:
            filename = f"ui_test_image/{task_id}.png"
            image_byte_array = io.BytesIO()
            image_base.save(image_byte_array, format='PNG')
            data["workflow_params"]["image_base"] = cos.upload(filename, image_byte_array.getvalue(), is_cdn=False,
                                                               content_type="image/png")
        if image_style:
            filename = f"ui_test_image/{task_id}_image_style.png"
            image_byte_array = io.BytesIO()
            image_style.save(image_byte_array, format='PNG')
            data["workflow_params"]["image_style"] = cos.upload(filename, image_byte_array.getvalue(), is_cdn=False,
                                                                content_type="image/png")

        res = requests.post(f"{Config.docs_host}/prompt", json=data, timeout=(300, 300))
        assert res.status_code == 200, gr.Warning(f"请求失败：{res.text}")
        if res.json()["code"] == 0:
            assert task_id == res.json()["request_id"]
            return res.json()["data"].get("preview_image", None), res.text
        else:
            return None, res.text
    except Exception as e:
        return None, str(e)


def run_param_api(workflow_id, params_code):
    try:
        assert workflow_id, gr.Warning("请先选择工作流")
        task_id = "TEST-" + str(time.time()).replace(".", "")
        data = json.loads(params_code)
        data["request_id"] = task_id
        data["workflow_id"] = workflow_id

        res = requests.post(f"{Config.docs_host}/prompt", json=data)
        assert res.status_code == 200, gr.Warning(f"请求失败：{res.text}")
        if res.json()["code"] == 0:
            assert task_id == res.json()["request_id"]
            return res.json()["data"].get("preview_image", None), res.text
        else:
            gr.Warning(f"请求失败：{res.json()['message']}"), res.text
    except Exception as e:
        return None, str(e)


def positive_prompt_storge(positive_prompt):
    request = PromptRequest(workflow_id=0, workflow_params={
        "positive_prompt": positive_prompt,
    })
    return prompt_chat_befor.run(request)


def translate(prompt):
    try:
        res = requests.post("https://translation.googleapis.com/language/translate/v2",
                            proxies={"https": "http://127.0.0.1:7890"},
                            headers={"X-goog-api-key": Config.google_api_key},
                            json={
                                "q": prompt,
                                "source": "zh-CN",
                                "target": "en",
                                "format": "text"
                            })
        assert res.status_code == 200, res.text
        return res.json()["data"]["translations"][0]["translatedText"]
    except Exception as e:
        gr.Warning("调用Google翻译失败：" + str(e))
        return prompt


def render_ui():
    with gr.Blocks(title="Comfyui-流程测试", css=f"{os.path.dirname(__file__)}/ui.css") as demo:
        workflow_id = gr.State(value="")
        with gr.Row():
            with gr.Column(variant="panel"):
                with gr.Tab("UI测试") as ui_tab:
                    with gr.Group() as positive_group:
                        positive_prompt = gr.Textbox(label="正向提示词", lines=4)
                        with gr.Row():
                            prompt_storge = gr.Button(value="提示词增强", size="sm")
                            translate_p = gr.Button(value="中文翻译", size="sm")
                    with gr.Group() as negative_group:
                        negative_prompt = gr.Textbox(label="反向提示词", lines=4)
                        translate_n = gr.Button(value="中文翻译", size="sm")
                    with gr.Row():
                        similarity = gr.Number(label="相似度(0~1)", minimum=0.1, maximum=1, step=0.1, value=1)
                        seed = gr.Number(value=-1, label="随机种子(0或-1代表随机))", minimum=-1, maximum=999999999999999, step=1)
                    image_base = gr.Image(label="底图", type="pil")
                    image_style = gr.Image(label="风格图片", type="pil")
                    with gr.Row(equal_height=False):
                        run_btn = gr.Button(value="运行", variant="primary")
                with gr.Tab("参数测试") as param_tab:
                    params_code = gr.Code(label="请求参数", language="javascript", interactive=True)
                    with gr.Row(equal_height=False):
                        run_param_btn = gr.Button(value="运行", variant="primary")
            with gr.Column():
                text_result = gr.Code(label="响应参数", language="javascript")
                image_result = gr.Image(label="结果图片（如果有）", scale=5, type="pil")

    demo.test_inputs = [positive_prompt, positive_group, negative_prompt, negative_group, similarity, image_base,
                        image_style,
                        params_code, seed]
    demo.workflow_id = workflow_id
    run_btn.click(run_api,
                  inputs=[workflow_id, positive_prompt, negative_prompt, similarity, image_base, image_style, seed
                          ], outputs=[image_result, text_result])
    run_param_btn.click(run_param_api, inputs=[workflow_id, params_code], outputs=[image_result, text_result])
    prompt_storge.click(positive_prompt_storge, inputs=[positive_prompt], outputs=[positive_prompt])
    translate_p.click(translate, inputs=[positive_prompt], outputs=[positive_prompt])
    translate_n.click(translate, inputs=[negative_prompt], outputs=[negative_prompt])
    return demo


if __name__ == '__main__':
    render_ui().queue().launch()
