from collections import deque
import numpy as np

class SimpleSmoother:
    def __init__(self, window=5):
        self.q = deque(maxlen=window)
    def update(self, x):
        if x is None:
            return None
        self.q.append(float(x))
        return float(sum(self.q) / len(self.q))
