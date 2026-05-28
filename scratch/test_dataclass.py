from dataclasses import dataclass, field

@dataclass
class RawJob:
    title: str
    extra: dict = field(default_factory=dict)

r1 = RawJob(title="Test")
print("r1.extra =", r1.extra)
r2 = RawJob(title="Test2", extra={})
print("r2.extra =", r2.extra)
r3 = RawJob(title="Test3", extra=None)
print("r3.extra =", r3.extra)
