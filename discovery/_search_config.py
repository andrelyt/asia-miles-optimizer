"""Search bounds and structural assumptions, separate from award policy."""
import copy
import json
import math
from pathlib import Path

from ._validation import ValidationError

CONFIG = Path(__file__).resolve().parents[1] / "config" / "search_config.json"


def search_config(supplied=None, candidates=False):
    config = copy.deepcopy(supplied) if supplied is not None else json.loads(CONFIG.read_text())
    try:
        bounds = config["route_search"]
        for key in ("max_flight_legs_per_trip", "max_connections", "max_raw_paths_per_od", "beam_width"):
            value = bounds[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < (0 if key == "max_connections" else 1):
                raise ValidationError("invalid route_search." + key)
        if candidates:
            generation = config["candidate_generation"]
            value = generation["max_candidates_per_strategy"]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError("invalid max_candidates_per_strategy")
            if not isinstance(generation["preserve_strategy_diversity"], bool):
                raise ValidationError("preserve_strategy_diversity must be boolean")
            threshold = generation["longhaul_distance_threshold_miles"]
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
                raise ValidationError("longhaul_distance_threshold_miles must be finite and positive")
            generation["longhaul_distance_threshold_miles"] = float(threshold)
    except (KeyError, TypeError) as exc:
        raise ValidationError("missing/invalid search config") from exc
    return config
