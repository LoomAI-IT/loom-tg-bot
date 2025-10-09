from typing import Protocol
from abc import abstractmethod

from internal import model


class IStateService(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def state_by_account_id(self, account_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            organization_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
            can_show_alerts: bool = None,
            show_error_recovery: bool = None,
    ) -> None: pass

    @abstractmethod
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None: pass

    @abstractmethod
    async def set_cache_file(self, filename: str, file_id: str) -> None: pass

    # Методы для работы с Vizard video cut alerts
    @abstractmethod
    async def create_vizard_video_cut_alert(
        self,
        state_id: int,
        youtube_video_reference: str,
        video_count: int
    ) -> int: pass

    @abstractmethod
    async def create_publication_approved_alert(self, state_id: int, publication_id: int) -> int: pass

    @abstractmethod
    async def create_publication_rejected_alert(self, state_id: int, publication_id: int) -> int: pass



class IStateRepo(Protocol):

    @abstractmethod
    async def create_state(self, tg_chat_id: int, tg_username: str) -> int: pass

    @abstractmethod
    async def state_by_id(self, tg_chat_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def state_by_account_id(self, account_id: int) -> list[model.UserState]: pass

    @abstractmethod
    async def set_cache_file(self, filename: str, file_id: str): pass

    @abstractmethod
    async def get_cache_file(self, filename: str) -> list[model.CachedFile]: pass

    @abstractmethod
    async def change_user_state(
            self,
            state_id: int,
            account_id: int = None,
            organization_id: int = None,
            access_token: str = None,
            refresh_token: str = None,
            can_show_alerts: bool = None,
            show_error_recovery: bool = None,
    ) -> None: pass

    @abstractmethod
    async def delete_state_by_tg_chat_id(self, tg_chat_id: int) -> None: pass

    # Методы для работы с Vizard video cut alerts
    @abstractmethod
    async def create_vizard_video_cut_alert(
        self,
        state_id: int,
        youtube_video_reference: str,
        video_count: int
    ) -> int: pass

    @abstractmethod
    async def get_vizard_video_cut_alert_by_state_id(
        self,
        state_id: int
    ) -> list[model.VizardVideoCutAlert]: pass

    @abstractmethod
    async def delete_vizard_video_cut_alert(self, state_id: int) -> None: pass

    @abstractmethod
    async def create_publication_approved_alert(self, state_id: int, publication_id: int) -> int: pass

    @abstractmethod
    async def get_publication_approved_alert_by_state_id(self, state_id: int) -> list[model.PublicationApprovedAlert]: pass

    @abstractmethod
    async def delete_publication_approved_alert(self, state_id: int) -> None: pass

    @abstractmethod
    async def create_publication_rejected_alert(self, state_id: int, publication_id: int) -> int: pass

    @abstractmethod
    async def get_publication_rejected_alert_by_state_id(self, state_id: int) -> list[model.PublicationRejectedAlert]: pass

    @abstractmethod
    async def delete_publication_rejected_alert(self, state_id: int) -> None: pass
