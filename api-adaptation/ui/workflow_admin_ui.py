import os.path
import gradio as gr
import ui.workflow_docs_ui as docs_ui
import ui.workflow_task_ui as task_ui
import ui.workflow_config_ui as config_ui


def render_ui():
    with gr.Blocks(title="Comfyui-管理后台", css=f"{os.path.dirname(__file__)}/ui.css") as demo:
        gr.Markdown("# Comfyui-管理后台")
        with gr.Tab("任务记录"):
            task_ui.render_ui()
        with gr.Tab("流程配置"):
            config_ui.render_ui()
        with gr.Tab("流程接口"):
            docs_ui.render_ui()

    # demo.auth = [
    #     ["admin", "admin"]
    # ]
    # demo.auth_message = "Comfyui-管理后台"
    return demo


def mount_workflow_admin(app):
    app = gr.mount_gradio_app(app, render_ui(), path="/workflow-admin")
    return app


if __name__ == '__main__':
    render_ui().queue().launch()
