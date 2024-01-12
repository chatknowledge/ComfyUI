import requests

from api.fastapp import logger
from api.models import PromptRequest

API_URL = "http://36.133.178.72:10010/enhance_prompt"


def run(request: PromptRequest):
    try:
        logger.info(f"===>提示词增强：{request.request_id} {request.workflow_params['positive_prompt']}")
        res = requests.post(API_URL, json={"prompt": request.workflow_params["positive_prompt"]})
        assert res.status_code == 200, res.text
        request.workflow_params["positive_prompt"] = res.json()["prompt"]
        return res.json()[0]
    except Exception as e:
        logger.exception(e)
        return request.workflow_params['positive_prompt']
