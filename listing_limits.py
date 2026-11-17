"""Call-history page limits adapted from MultiWA (MIT). See third_party/multiwa/NOTICE.md."""
import math


def message_page_size(value):
    try:
        if isinstance(value,bool):return 50
        n=float(value)
        return min(math.floor(n),500) if math.isfinite(n) and n>=1 else 50
    except (ValueError,TypeError,OverflowError):return 50
