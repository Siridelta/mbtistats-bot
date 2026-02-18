from asyncio import sleep
import asyncio
import nonebot
from nonebot.adapters.qq import Adapter as QQAdapter
from nonebot.adapters.console import Adapter as ConsoleAdapter
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册 Adapters
driver = nonebot.get_driver()
driver.register_adapter(QQAdapter)
driver.register_adapter(ConsoleAdapter)
driver.register_adapter(OneBotV11Adapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
