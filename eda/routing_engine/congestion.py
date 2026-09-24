# Global Routing Congestion Grid & Hotspot Estimator
from typing import Dict, List, Any, Tuple
import math

class GCell:
    def __init__(self, x_idx: int, y_idx: int, x_min: float, y_min: float, x_max: float, y_max: float,
                 h_capacity: int = 24, v_capacity: int = 24):
        self.x_idx = x_idx
        self.y_idx = y_idx
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.h_capacity = h_capacity
        self.v_capacity = v_capacity
        self.h_demand = 0
        self.v_demand = 0

    @property
    def h_overflow(self) -> int:
        return max(0, self.h_demand - self.h_capacity)

    @property
    def v_overflow(self) -> int:
        return max(0, self.v_demand - self.v_capacity)

    @property
    def utilization(self) -> float:
        tot_cap = self.h_capacity + self.v_capacity
        tot_dem = self.h_demand + self.v_demand
        return round((tot_dem / max(1, tot_cap)) * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_idx": self.x_idx,
            "y_idx": self.y_idx,
            "x_min": round(self.x_min, 2),
            "y_min": round(self.y_min, 2),
            "x_max": round(self.x_max, 2),
            "y_max": round(self.y_max, 2),
            "h_capacity": self.h_capacity,
            "v_capacity": self.v_capacity,
            "h_demand": self.h_demand,
            "v_demand": self.v_demand,
            "utilization": self.utilization,
            "is_hotspot": self.utilization > 80.0
        }

class CongestionEstimator:
    def __init__(self, core_x: float, core_y: float, core_w: float, core_h: float, grid_size: int = 12):
        self.core_x = core_x
        self.core_y = core_y
        self.core_w = core_w
        self.core_h = core_h
        self.grid_size = grid_size
        self.tile_w = core_w / float(grid_size)
        self.tile_h = core_h / float(grid_size)
        self.grid: List[List[GCell]] = []
        self._build_grid()

    def _build_grid(self):
        self.grid = []
        for yi in range(self.grid_size):
            row = []
            y_min = self.core_y + yi * self.tile_h
            y_max = y_min + self.tile_h
            for xi in range(self.grid_size):
                x_min = self.core_x + xi * self.tile_w
                x_max = x_min + self.tile_w
                row.append(GCell(xi, yi, x_min, y_min, x_max, y_max))
            self.grid.append(row)

    def get_cell_coords(self, x: float, y: float) -> Tuple[int, int]:
        xi = max(0, min(self.grid_size - 1, int((x - self.core_x) / self.tile_w)))
        yi = max(0, min(self.grid_size - 1, int((y - self.core_y) / self.tile_h)))
        return xi, yi

    def add_route_demand(self, x1: float, y1: float, x2: float, y2: float):
        xi1, yi1 = self.get_cell_coords(x1, y1)
        xi2, yi2 = self.get_cell_coords(x2, y2)

        min_x, max_x = min(xi1, xi2), max(xi1, xi2)
        min_y, max_y = min(yi1, yi2), max(yi1, yi2)

        # L-shaped routing: horizontal segment then vertical
        for x in range(min_x, max_x + 1):
            if x < self.grid_size and yi1 < self.grid_size:
                self.grid[yi1][x].h_demand += 1

        for y in range(min_y, max_y + 1):
            if xi2 < self.grid_size and y < self.grid_size:
                self.grid[y][xi2].v_demand += 1

    def calculate_metrics(self) -> Dict[str, Any]:
        total_gcells = self.grid_size * self.grid_size
        total_demand = 0
        total_capacity = 0
        total_overflow = 0
        hotspot_count = 0
        max_util = 0.0

        flat_gcells = []
        for row in self.grid:
            for gcell in row:
                flat_gcells.append(gcell.to_dict())
                total_demand += (gcell.h_demand + gcell.v_demand)
                total_capacity += (gcell.h_capacity + gcell.v_capacity)
                total_overflow += (gcell.h_overflow + gcell.v_overflow)
                if gcell.utilization > 80.0:
                    hotspot_count += 1
                if gcell.utilization > max_util:
                    max_util = gcell.utilization

        avg_congestion_pct = round((total_demand / max(1, total_capacity)) * 100, 1)

        # DRC risk heuristic
        if total_overflow == 0 and avg_congestion_pct < 60:
            drc_risk = "LOW"
        elif avg_congestion_pct < 85:
            drc_risk = "MODERATE"
        else:
            drc_risk = "HIGH"

        return {
            "average_congestion_pct": avg_congestion_pct,
            "max_tile_congestion_pct": max_util,
            "hotspot_tiles_count": hotspot_count,
            "overflow_tracks_count": total_overflow,
            "estimated_drc_risk": drc_risk,
            "grid_dimensions": f"{self.grid_size}x{self.grid_size}",
            "gcells": flat_gcells
        }
