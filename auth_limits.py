"""Thread-safe bounded authentication budgets without storing raw account identifiers."""
import hashlib


def consume(buckets,lock,address,identity,stamp):
    identity=identity[:512].strip().casefold() if isinstance(identity,str) else ''
    key=hashlib.sha256(identity.encode()).hexdigest()
    with lock:
        for old,values in list(buckets.items()):
            recent=[value for value in values if value>stamp-60]
            if recent:buckets[old]=recent
            else:buckets.pop(old,None)
        ip=('address',address);account=('account',address,key)
        if len(buckets.get(ip,[]))>=120:return False
        buckets.setdefault(ip,[]).append(stamp)
        if len(buckets.get(account,[]))>=12:return False
        if account not in buckets and len(buckets)>=8192:return False
        buckets.setdefault(account,[]).append(stamp);return True
