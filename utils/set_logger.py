import os
import time
import logging
from pathlib import Path

def set_logger(log_name:str):
    time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / '.project_root').exists():
            root = p
            break
    else:
        raise RuntimeError('Can not find project root')
    LOG_PATH = os.path.join(
        root, "log", log_name, f"{time_str}.log"
    )
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_PATH)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(stream_handler)

    return logger