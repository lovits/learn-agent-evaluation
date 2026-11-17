"""TinyRAG's BaseEmbeddings; provider imports and environment side effects omitted.

Adapted from Datawhale TinyRAG, by 不要葱姜蒜 and contributors.
CC BY-NC-SA 4.0; see LICENSE.md. The cosine calculation is unchanged.
"""

import numpy as np


class BaseEmbeddings:
    def __init__(self, path: str, is_api: bool) -> None:
        self.path = path
        self.is_api = is_api

    def get_embedding(self, text: str, model: str) -> list[float]:
        raise NotImplementedError

    @classmethod
    def cosine_similarity(cls, vector1, vector2) -> float:
        dot_product = np.dot(vector1, vector2)
        magnitude = np.linalg.norm(vector1) * np.linalg.norm(vector2)
        if not magnitude:
            return 0
        return dot_product / magnitude
