def format_duration(seconds: int) -> str:
    if not seconds:
        return "0:00"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_count(n: int, singular: str, plural: str | None = None) -> str:
    if n == 1:
        return f"1 {singular}"
    return f"{n} {plural or singular + 's'}"
