# comfyui-api-adaptation

用于适配ComfyUI的API，增加一些自己的功能


## Structure
```md
comfyui-api-adaptation
├── LICENSE
├── README.md
├── api                # api接口相关
│   ├── fastapp.py     # fastapi的配置
│   └── models.py      # api接口的数据模型
├── config
│   ├── __init__.py    # 配置加载
├── db
│   ├── __init__.py    # 数据库初始化
│   └── models.py      # 数据库模型
├── requirements.txt
├── service
│   ├── comfy_nodes_client.py  # comfy节点调用相关
│   ├── cos_service.py         # cos相关
│   ├── error_defind.py        # 错误定义
│   ├── my_thread.py
│   └── workflow_service.py    # workflow相关服务
└── ui
    ├── workflow_config_ui.py  # workflow配置UI
    └── workflow_docs_ui.py    # workflow文档UI
├── main.py            # 主程序执行入口

```

### 安装

```bash
# pyton3.7+
pip install -r requirements.txt
```


### Config By Env File `.env` Or Set Env
.evn
```py
comfyui_node_hosts="comfyui-node1:8545,comfyui-node2:8545,comfyui-node3:8545"
api_port=8000   # api port
comfyui_ui_hosts="http://comfyui-ui:3000"  # comfyui-ui host
cos_config=""   # cos josn config
db_connection_stringion_string="sqlite:///database.sqlite"  # mysql or sqlite or other`

```
set env
```bash
export comfyui_node_hosts="comfyui-node1:8545,comfyui-node2:8545,comfyui-node3:8545"
export api_port=8000   # api port
export comfyui_ui_hosts="http://comfyui-ui:3000"  # comfyui-ui host
export cos_config=""   # cos josn config
export db_connection_stringion_string="sqlite:///database.sqlite"  # mysql or sqlite or other`
```


### Start 
```bash
cd ~/comfyui-api-adaptation
python3 main.py
```