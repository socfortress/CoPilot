from enum import Enum


class WazuhAgentsTemplatePaths(Enum):
    LINUX_AGENT = ("templates", "linux_agent.conf")
    WINDOWS_AGENT = ("templates", "windows_agent.conf")
    MAC_AGENT = ("templates", "mac_agent.conf")
