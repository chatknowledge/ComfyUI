import os.path

import json
from loguru import logger
from qcloud_cos import CosS3Client, CosConfig
from retry import retry

from config import Config


class CosService(object):
    def __init__(self, config=Config.comfyui_cos_config):
        self.config = json.loads(config)
        self.oss_client = CosS3Client(
            CosConfig(
                Scheme="https",
                Region=self._cos_config("region"),
                SecretId=self._cos_config("secret_id"),
                SecretKey=self._cos_config("secret_key")))
        self.Bucket = self._cos_config("bucket")
        self.prefix = self._cos_config("prefix")

    def _cos_config(self, name):
        return self.config[name]

    def _get_text(self, path):
        response = self.oss_client.get_object(
            Bucket=self._cos_config("bucket"),
            Key=os.path.join(self._cos_config("prefix"), path)
        )
        return str(response['Body'].get_raw_stream().data, encoding='utf-8')

    def get_workflow_api_json(self, cos_key):
        """从COS上获取工作流配置"""
        return self._get_text(cos_key)

    def get_workflow_json(self, cos_key):
        """从COS上获取工作流配置"""
        return self._get_text(cos_key)

    @retry(ConnectionError, tries=3, delay=2)
    def upload(self, filename, body, is_cdn=True, is_public=True, content_type=None):
        filename = filename.replace("\\", "/")
        key = os.path.join(self._cos_config("prefix"), filename)
        logger.info("开始COS上传:{}", key)
        # 本地路径 简单上传
        self.oss_client.put_object(
            Bucket=self._cos_config("bucket"),
            Body=body,
            Key=key,
            ContentType=content_type
        )
        if is_cdn and "cdn" in self.config and self.config["cdn"] != "":
            url = f"https://{self._cos_config('cdn')}{key}"
        else:
            url = f"https://{self._cos_config('bucket')}.cos.{self._cos_config('region')}.myqcloud.com{key}"
        logger.info("完成COS上传:{}", url)
        if is_public:
            self.oss_client.put_object_acl(
                Key=key,
                Bucket=self._cos_config("bucket"),
                ACL='public-read'
            )
            logger.info(f"完成ACL")
        return url

    @retry(ConnectionError, tries=3, delay=2)
    def upload_config(self, filename, body):
        filename = filename.replace("\\", "/")
        key = os.path.join(self._cos_config("prefix"), filename)
        logger.info("开始COS上传:{}", key)
        # 本地路径 简单上传
        self.oss_client.put_object(
            Bucket=self._cos_config("bucket"),
            Body=body,
            Key=key,
        )
        url = f"https://{self._cos_config('bucket')}.cos.{self._cos_config('region')}.myqcloud.com{key}"
        logger.info("完成COS上传:{}", url)
        return key
