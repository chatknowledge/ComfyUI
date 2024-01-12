class ComfyParamError(Exception):
    """ComfyUI参数错误"""
    Code = 40001


class ComfyInvokeError(Exception):
    """ComfyUI请求错误"""
    Code = 40002


class WorkflowNoFoundError(Exception):
    """工作流不存在"""
    Code = 40003


class ComfyParameterizationError(Exception):
    """服务内部进行参数化错误"""
    Code = 40004


class WorkflowTaskNoFoundError(Exception):
    """工作流任务不存在"""
    Code = 40005


class WorkflowTaskExistError(Exception):
    """工作流任务已存在"""
    Code = 40006


class ComfyuiViewImageError(Exception):
    """查看图片失败"""
    Code = 40007


class ComfyuiTaksWaitError(Exception):
    """获取任务结果失败"""
    Code = 40008
