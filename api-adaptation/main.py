import os.path
from loguru import logger
from api.fastapp import run

logs_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(logs_dir, exist_ok=True)

logger.add(f'{logs_dir}/debug.log', rotation='00:00', retention='15 days', level="DEBUG")
logger.add(f'{logs_dir}/info.log', rotation='00:00', retention='15 days', level="INFO")
logger.add(f'{logs_dir}/error.log', rotation='00:00', retention='15 days', level="ERROR")

if __name__ == '__main__':
    run()
