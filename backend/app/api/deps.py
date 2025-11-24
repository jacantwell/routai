from fastapi import Request, Depends
from app.api.services import SessionManager
from typing import Annotated

async def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager

SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]