import nonebot
from nonebot.adapters.qq import Adapter as QQAdapter
from nonebot.adapters.console import Adapter as ConsoleAdapter

# 初始化 NoneBot
nonebot.init()

# 注册 Adapters
driver = nonebot.get_driver()
driver.register_adapter(QQAdapter)
driver.register_adapter(ConsoleAdapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")
nonebot.load_builtin_plugins("echo", "single_session")

if __name__ == "__main__":
    nonebot.run()
