"""Directed, evidence-bearing route snapshot. Routes never imply award seats."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from ._search_config import search_config
from ._validation import ValidationError, parse_date, validate


def stable_id(prefix, value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return prefix + hashlib.sha256(encoded.encode()).hexdigest()[:24]


def route_status(edges):
    if not edges:
        return "UNVERIFIED"
    statuses = {edge["route_status"] for edge in edges}
    return "UNVERIFIED" if "UNVERIFIED" in statuses else "STALE" if "STALE" in statuses else "VERIFIED"


def _path_key(path):
    return len(path), sum(e["distance_miles"] for e in path), tuple(e["edge_id"] for e in path)


class RouteGraph:
    def __init__(self, supplied):
        snapshot = copy.deepcopy(supplied)
        validate(snapshot, "route_graph.schema.json")
        self.snapshot_id = snapshot["snapshot_id"]
        self.observed_at = snapshot["observed_at"]
        observed_date = datetime.fromisoformat(self.observed_at.upper().replace("Z", "+00:00")).date()
        self._adjacency = {}
        self._edges = {}
        identities = {}
        for raw in snapshot["edges"]:
            edge = copy.deepcopy(raw)
            if edge["origin"] == edge["destination"]:
                raise ValidationError("self-loop route is not a flight relationship")
            start, end = edge.get("valid_from"), edge.get("valid_until")
            if start and end and parse_date(start) > parse_date(end):
                raise ValidationError("route valid_from exceeds valid_until")
            edge["cabins"] = sorted(edge["cabins"])
            edge["distance_miles"] = float(edge["distance_miles"])
            edge["observed_at"] = edge.get("observed_at") or self.observed_at
            for key in ("alliance", "distance_source", "source_url", "valid_from", "valid_until"):
                edge.setdefault(key, None)
            identity = tuple(edge[k] for k in ("origin", "destination", "operating_carrier", "valid_from", "valid_until"))
            if identity in identities and identities[identity] != edge:
                raise ValidationError("conflicting duplicate route relationship")
            identities[identity] = copy.deepcopy(edge)
            edge["declared_route_status"] = edge["route_status"]
            notes = []
            try:
                url = urlparse(edge["source_url"] or "")
                source_present = url.scheme in ("http", "https") and bool(url.netloc)
            except ValueError:
                source_present = False
            if edge["route_status"] == "VERIFIED" and not source_present:
                edge["route_status"] = "UNVERIFIED"
                notes.append("VERIFIED_WITHOUT_SOURCE_URL")
            if end and parse_date(end) < observed_date and edge["route_status"] == "VERIFIED":
                edge["route_status"] = "STALE"
                notes.append("VALIDITY_EXPIRED_AT_SNAPSHOT")
            edge["evidence_notes"] = notes
            edge["edge_id"] = stable_id("edge_", edge)
            self._edges[edge["edge_id"]] = edge
        for edge in self._edges.values():
            self._adjacency.setdefault(edge["origin"], []).append(edge)
        for edges in self._adjacency.values():
            edges.sort(key=lambda e: (e["destination"], e["operating_carrier"], e["edge_id"]))

    def edges(self):
        return copy.deepcopy(sorted(self._edges.values(), key=lambda e: e["edge_id"]))

    def find_paths(self, origin, destination, config=None, travel_date=None, max_legs=None):
        """Bounded simple directed paths; no reverse inference or cycle expansion.

        Without a travel date, validity is NOT_CHECKED; expired snapshot evidence
        can be STALE. With a date, known out-of-range relationships are excluded.
        """
        bounds = search_config(config)["route_search"]
        for airport in (origin, destination):
            if not isinstance(airport, str) or not re.fullmatch("[A-Z]{3}", airport):
                raise ValidationError("path endpoints must be IATA airport codes")
        if max_legs is not None and (isinstance(max_legs, bool) or not isinstance(max_legs, int) or max_legs < 1):
            raise ValidationError("max_legs must be positive integer")
        day = parse_date(travel_date) if travel_date is not None else None
        limit = min(bounds["max_flight_legs_per_trip"], bounds["max_connections"] + 1, max_legs or bounds["max_flight_legs_per_trip"])
        frontier, paths = [([], (origin,))], []
        rejected_dates = 0
        beam_truncated = False
        path_limit_reached = False
        if origin == destination:
            return {"paths": [], "diagnostics": {"code": "SAME_ENDPOINTS", "validity_status": "NOT_CHECKED"}}
        for _ in range(limit):
            next_frontier = []
            for path, airports in frontier:
                for edge in self._adjacency.get(airports[-1], []):
                    if edge["destination"] in airports:
                        continue
                    if day and ((edge["valid_from"] and day < parse_date(edge["valid_from"])) or
                                (edge["valid_until"] and day > parse_date(edge["valid_until"]))):
                        rejected_dates += 1
                        continue
                    candidate = path + [edge]
                    if edge["destination"] == destination:
                        paths.append(candidate)
                        if len(paths) >= bounds["max_raw_paths_per_od"]:
                            path_limit_reached = True
                            break
                    elif len(candidate) < limit:
                        next_frontier.append((candidate, airports + (edge["destination"],)))
                        if len(next_frontier) > bounds["beam_width"]:
                            beam_truncated = True
                            next_frontier.sort(key=lambda p: _path_key(p[0]))
                            next_frontier.pop()
                if path_limit_reached:
                    break
            if path_limit_reached:
                break
            next_frontier.sort(key=lambda p: _path_key(p[0]))
            beam_truncated |= len(next_frontier) > bounds["beam_width"]
            frontier = next_frontier[:bounds["beam_width"]]
            if not frontier:
                break
        return {"paths": copy.deepcopy(sorted(paths, key=_path_key)), "diagnostics": {
            "code": "PATHS_FOUND" if paths else "NO_PATH_WITHIN_BOUNDS",
            "beam_truncated": beam_truncated, "path_limit_reached": path_limit_reached,
            "date_exclusions": rejected_dates, "validity_status": "CHECKED" if day else "NOT_CHECKED",
            "max_legs_used": limit,
        }}


def load_route_graph(source):
    if isinstance(source, (str, Path)):
        source = json.loads(Path(source).read_text(encoding="utf-8"))
    return RouteGraph(source)
