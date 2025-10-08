from aiogram_dialog import DialogManager

from internal import interface, model
from pkg.log_wrapper import auto_log
from pkg.trace_wrapper import traced_method


class GenerateVideoCutGetter(interface.IGenerateVideoCutGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            state_repo: interface.IStateRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.state_repo = state_repo

    @auto_log()
    @traced_method()
    async def get_youtube_input_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        is_processing_video = False
        if dialog_manager.start_data:
            if dialog_manager.start_data.get("is_processing_video"):
                self.logger.info("Видео в процессе обработки из start_data")
                is_processing_video = True
        else:
            is_processing_video = dialog_manager.dialog_data.get("is_processing_video", False)
            if is_processing_video:
                self.logger.info("Видео в процессе обработки из dialog_data")

        data = {
            "is_processing_video": is_processing_video,
            "has_invalid_youtube_url": dialog_manager.dialog_data.get("has_invalid_youtube_url", False),
        }
        return data
