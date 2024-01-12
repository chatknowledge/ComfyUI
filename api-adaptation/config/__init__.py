import os
from dotenv import load_dotenv

load_dotenv(verbose=True)


class Config(object):
    # comfyui的计算节点地址
    google_api_key = os.getenv("google_api_key")
    comfyui_node_hosts = os.getenv("comfyui_node_hosts", "http://127.0.0.1:8188,http://127.0.0.1:8188")
    # 本项目开放接口的端口
    api_port = int(os.getenv("api_port", "8000"))
    # comfyui动态参数配置地址
    comfyui_ui_hosts = os.getenv("comfyui_ui_hosts", "http://127.0.0.1:8188")
    # Cos存储配置(JSON格式)
    comfyui_cos_config = os.getenv("comfyui_cos_config")
    image_cos_config = os.getenv("image_cos_config", comfyui_cos_config)
    # 数据库地址
    db_connection_string = os.getenv("db_connection_string", f"sqlite:///{os.path.dirname(__file__)}/database.sqlite")
    # 默认租户id
    default_tenant_id = os.getenv("default_tenant_id", -1)
    # docs文档地址
    docs_host = os.getenv("docs_host", "http://5slive.com:3000")
    # 大模型的地址
    big_model_path = os.getenv("big_model_path", None)
