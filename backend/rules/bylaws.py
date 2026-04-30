from dataclasses import dataclass

from rules.bylaw_repository import get_bylaw_profile_payload


@dataclass(frozen=True)
class BylawProfile:
    profile_id: str = "default"
    min_stair_width_ft: float = 4.0
    min_exit_width_ft: float = 4.0
    min_corridor_width_ft: float = 5.0
    min_room_area_sqft: float = 80.0
    max_floors_without_lift: int = 3


DEFAULT_PROFILE = BylawProfile()


def get_bylaw_profile(profile_id: str | None) -> BylawProfile:
    raw = get_bylaw_profile_payload(profile_id)
    return BylawProfile(
        profile_id=str(raw.get("profile_id", "default")),
        min_stair_width_ft=float(raw.get("min_stair_width_ft", DEFAULT_PROFILE.min_stair_width_ft)),
        min_exit_width_ft=float(raw.get("min_exit_width_ft", DEFAULT_PROFILE.min_exit_width_ft)),
        min_corridor_width_ft=float(raw.get("min_corridor_width_ft", DEFAULT_PROFILE.min_corridor_width_ft)),
        min_room_area_sqft=float(raw.get("min_room_area_sqft", DEFAULT_PROFILE.min_room_area_sqft)),
        max_floors_without_lift=int(raw.get("max_floors_without_lift", DEFAULT_PROFILE.max_floors_without_lift)),
    )
