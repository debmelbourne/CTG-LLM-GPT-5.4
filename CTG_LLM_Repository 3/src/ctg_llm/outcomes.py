"""CTU-UHB outcome mapping from the three available composite components."""
import math


def ctu_asphyxia(apgar5=None, arterial_ph=None, base_excess=None):
    """One positive component gives 1; unresolved absence remains None."""
    values = []
    for value, threshold in ((apgar5, 5), (arterial_ph, 7.0), (base_excess, -12.0)):
        if value is None:
            values.append(None)
        else:
            value = float(value)
            if not math.isfinite(value):
                values.append(None)
            else:
                values.append(value <= threshold if threshold == -12.0 else value < threshold)
    if any(x is True for x in values):
        return 1
    if all(x is False for x in values):
        return 0
    return None
