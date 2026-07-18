from ..exceptions import InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class DialogTool(BaseTool):
    name = "dialog"
    description = "Configure or inspect browser dialogs (alert/confirm/prompt)"

    def run(self, action: str = "last", handle: str = "dismiss",
            prompt_text: str = None) -> ToolResponse:
        try:
            tab_id = self.browser.active_tab_id
            if action == "last":
                record = self.browser.get_last_dialog(tab_id)
                if record is None:
                    return ToolResponse.ok(tool=self.name, message="No dialog recorded")
                return ToolResponse.ok(tool=self.name, message="Last dialog info",
                                       data={
                                           "type": record.dialog_type,
                                           "message": record.message,
                                           "action_taken": record.action_taken,
                                       })
            elif action == "configure":
                self.browser.set_dialog_policy(tab_id, handle, prompt_text)
                return ToolResponse.ok(tool=self.name,
                                       message=f"Dialog policy set to '{handle}'")
            else:
                raise InvalidToolParamsError(f"Unknown dialog action '{action}'")
        except InvalidToolParamsError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Dialog operation failed",
                                     error=str(exc), error_code="dialog_error")
