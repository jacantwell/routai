import logging
from typing import Any, Dict

from app.models import AgentState
from app.utils import get_accommodation

logger = logging.getLogger(__name__)


def find_accommodation_node(state: AgentState) -> Dict[str, Any]:
    """Find accommodation and determine if optimization needed."""

    segments = state.segments

    if not segments:
        error_msg = "Accommodaion search requires validated segments"
        raise ValueError(error_msg)

    logger.info(f"Finding accommodation for {len(segments)} nights")

    days_without_accommodation = []

    for seg in segments:
        accommodation_opts = get_accommodation(seg.route.destination.coordinates)
        seg.accommodation_options += accommodation_opts
        if len(seg.accommodation_options) == 0:
            days_without_accommodation.append(seg.day)

    return {
        "segments": segments,
    }
