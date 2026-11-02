"""Risk balı (0–100): yoxlanılmış tapıntılardan kodla hesablanır, model rəqəm vermir.

Hər tapıntı xal verir: kritik 20, orta 8, aşağı 3. Bal = 100 · (1 − e^(−xal/60)):
az tapıntıda xəttə yaxın artır, çox tapıntıda 100-ə yaxınlaşır, amma keçmir.
Məsələn: 1 kritik → 28, 3 kritik → 63, 5 kritik + 8 orta → 94.
"""

import math
from dataclasses import dataclass

from agent.verifier import Finding

WEIGHTS = {"kritik": 20, "orta": 8, "aşağı": 3}
SCALE = 60

# (yuxarı hədd, ad, rəng) — balın hansı aralığa düşdüyü
LEVELS = [
    (25, "aşağı risk", "green"),
    (50, "orta risk", "orange"),
    (75, "yüksək risk", "red"),
    (101, "çox yüksək risk", "red"),
]


@dataclass
class Score:
    value: int
    level: str
    color: str
    points: int


def score(findings: list[Finding]) -> Score:
    points = sum(WEIGHTS[f.risk] for f in findings)
    value = round(100 * (1 - math.exp(-points / SCALE)))
    level, color = next((name, color) for limit, name, color in LEVELS if value < limit)
    return Score(value, level, color, points)
