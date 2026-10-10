import numpy as np

PRECISION = 10


def normalize_float(x):
    """Округление float или массива float.
    Убирает погрешности при сравнении координат узлов.

    normalize_float(3.1415926535)       → 3.1415926535
    normalize_float([0.1, 0.2])         → [0.1, 0.2]
    normalize_float(np.array([0.1, 0.2])) → array([0.1, 0.2])
    tuple(normalize_float([s, t]))      → (0.1, 0.2) — готовый ключ
    """
    if isinstance(x, (list, tuple)):
        return [round(v, PRECISION) for v in x]
    if isinstance(x, np.ndarray):
        return np.round(x, PRECISION)
    return round(x, PRECISION)