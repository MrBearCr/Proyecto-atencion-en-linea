"""
Adaptive chunk size controller for background data loads.
Adjusts next chunk size based on measured latency, with EMA smoothing and cooldown.
"""
from typing import Optional

class AdaptiveChunkController:
    def __init__(self,
                 initial: int = 500,
                 min_size: int = 100,
                 max_size: int = 2000,
                 target_latency: float = 2.0,
                 fast_ratio: float = 0.5,
                 slow_ratio: float = 1.2,
                 grow_factor: float = 1.3,
                 shrink_factor: float = 0.8,
                 ema_alpha: float = 0.4,
                 cooldown: int = 2):
        self.size = max(min_size, min(max_size, int(initial)))
        self.min_size = int(min_size)
        self.max_size = int(max_size)
        self.target = float(target_latency)
        self.fast_threshold = self.target * float(fast_ratio)
        self.slow_threshold = self.target * float(slow_ratio)
        self.grow_factor = float(grow_factor)
        self.shrink_factor = float(shrink_factor)
        self.ema_alpha = float(ema_alpha)
        self.ema: Optional[float] = None
        self.cooldown = int(cooldown)
        self.cooldown_left = 0

    def update(self, chunk_time: float, rows_returned: int) -> int:
        # Update EMA of latency
        if self.ema is None:
            self.ema = float(chunk_time)
        else:
            self.ema = self.ema_alpha * float(chunk_time) + (1.0 - self.ema_alpha) * self.ema

        # Decide grow/shrink/hold using EMA and cooldown
        if self.ema > self.slow_threshold:
            # Too slow => shrink
            self.size = max(self.min_size, int(self.size * self.shrink_factor))
            self.cooldown_left = self.cooldown
        elif self.ema < self.fast_threshold:
            # Fast => only grow if cooldown reached zero
            if self.cooldown_left <= 0:
                self.size = min(self.max_size, int(self.size * self.grow_factor))
                self.cooldown_left = self.cooldown
            else:
                self.cooldown_left -= 1
        else:
            # In the sweet spot => maintain and decay cooldown if any
            if self.cooldown_left > 0:
                self.cooldown_left -= 1
        return self.size

    def recommend_sleep(self, last_chunk_time: float) -> float:
        # Small adaptive pause to avoid overwhelming DB/UI
        # 10% of chunk time, clamped between 50ms and 500ms
        return max(0.05, min(0.5, float(last_chunk_time) * 0.1))
