from __future__ import annotations

import pandas as pd

from restaurant_rec.phase2.cities import distinct_cities
from restaurant_rec.phase2.localities import distinct_localities


def test_distinct_cities_sorted_unique() -> None:
    df = pd.DataFrame({"city": ["Mumbai", "Delhi", "mumbai", "", None, "Delhi"]})
    assert distinct_cities(df) == ["Delhi", "Mumbai"]


def test_distinct_localities_sorted_unique() -> None:
    df = pd.DataFrame({"locality": ["Koramangala", "Indiranagar", "koramangala", "", None, "Indiranagar"]})
    assert distinct_localities(df) == ["Indiranagar", "Koramangala"]
