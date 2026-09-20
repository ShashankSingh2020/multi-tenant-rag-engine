import math
from typing import List


def generate_mock_embedding(text: str, dimensions: int = 1536) -> List[float]:
    """
    Generates a deterministic unit-normalized embedding vector for tests/dev.
    """
    seed = sum(ord(c) for c in text[:100]) if text else 1
    raw = [math.sin(seed + i) for i in range(dimensions)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]