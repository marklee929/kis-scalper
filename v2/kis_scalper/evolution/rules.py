def should_evolve(summary) -> bool:
    return bool(summary.get("trigger", False))
