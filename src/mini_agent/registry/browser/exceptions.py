class BrowserAgentError(Exception):
    code: str = "browser_agent_error"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class BrowserNotStartedError(BrowserAgentError):
    code = "browser_not_started"


class NavigationError(BrowserAgentError):
    code = "navigation_error"


class ElementNotFoundError(BrowserAgentError):
    code = "element_not_found"


class AmbiguousElementError(BrowserAgentError):
    code = "ambiguous_element"


class BrowserTimeoutError(BrowserAgentError):
    code = "timeout"


class TabNotFoundError(BrowserAgentError):
    code = "tab_not_found"


class InvalidToolParamsError(BrowserAgentError):
    code = "invalid_params"


class UnknownToolError(BrowserAgentError):
    code = "unknown_tool"


class DialogError(BrowserAgentError):
    code = "dialog_error"


class DownloadError(BrowserAgentError):
    code = "download_error"


class ScriptExecutionError(BrowserAgentError):
    code = "script_execution_error"


class StorageError(BrowserAgentError):
    code = "storage_error"
