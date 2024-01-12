import requests

from api.fastapp import logger
from api.models import PromptRequest

API_URL = "http://36.133.178.72:10010/caption"


def run(request: PromptRequest):
    try:
        # request.workflow_params["similarity"] = 1
        if request.workflow_params.get("positive_prompt"):
            logger.info(f"===>ImageCaptionScript：{request.request_id} 已经有提示词结果了，不再请求")
            return
        logger.info(f"===>ImageCaptionScript：{request.request_id}")
        res = requests.post(API_URL, json={"image_url": request.workflow_params["image_base"]})
        assert res.status_code == 200, res.text
        request.workflow_params["positive_prompt"] = res.json()["caption"]
        return request
    except Exception as e:
        logger.exception(e)
        return request
