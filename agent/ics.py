"""Açar tarixləri təqvim faylına (.ics) çevirir — telefon, Outlook, Google Calendar açır.

Hadisələr: müqavilənin bitməsi, bitməyə yaxın xəbərdarlıq (yaşayışda 1 ildən uzun müqavilə üçün
Maddə 693.1.2-yə görə uzatma tələbinin son günü), aylıq ödəniş günləri.
"""

from datetime import UTC, date, datetime, timedelta

from agent.verifier import Result


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _months_before(day: date, months: int) -> date:
    month = day.month - months
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    for d in (day.day, 30, 29, 28):  # ayın sonu: 31 dekabr - 2 ay → 31 oktyabr, 30 aprel və s.
        try:
            return date(year, month, d)
        except ValueError:
            continue
    raise ValueError(day)


def events(result: Result) -> list[tuple[date, str, str, str | None]]:
    """(tarix, başlıq, izah, təkrar qaydası)"""
    s = result.summary
    out = []
    if s.bitme:
        out.append(
            (s.bitme, "İcarə müqaviləsi bitir", "Əmlakı qaytarmaq və ya müqaviləni uzatmaq.", None)
        )
        long_residential = (
            result.emlak_novu == "yaşayış" and s.baslangic and (s.bitme - s.baslangic).days > 366
        )
        if long_residential:
            out.append((
                _months_before(s.bitme, 2),
                "Son gün: müqavilənin uzadılmasını yazılı tələb etmək",
                (
                    "Mülki Məcəllə 693.1.2: bir ildən uzun yaşayış kirayəsində kirayəçi "
                    "münasibətlərin davam etdirilməsini ən geci bitməyə 2 ay qalmış yazılı "
                    "bildirişlə tələb edə bilər."
                ),
                None,
            ))  # fmt: skip
        else:
            out.append((s.bitme - timedelta(days=30), "Müqavilənin bitməsinə 30 gün qalıb",
                        "Uzatmaq və ya ləğv etmək barədə qərar verin.", None))  # fmt: skip
    if s.odenis_gunu and s.baslangic:
        first = s.baslangic.replace(day=min(s.odenis_gunu, 28))
        if first < s.baslangic:
            first = (first.replace(day=1) + timedelta(days=32)).replace(day=first.day)
        until = f";UNTIL={s.bitme:%Y%m%d}" if s.bitme else ""
        out.append((first, "İcarə haqqının ödənilməsi", "Aylıq icarə haqqı.",
                    f"FREQ=MONTHLY;BYMONTHDAY={min(s.odenis_gunu, 28)}{until}"))  # fmt: skip
    return out


def build(result: Result, title: str) -> bytes | None:
    """.ics faylının baytları; tarix yoxdursa None."""
    items = events(result)
    if not items:
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Muqavile agenti//AZ",
        "CALSCALE:GREGORIAN",
    ]
    for i, (day, summary, description, rule) in enumerate(items):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{stamp}-{i}@muqavile-agenti",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(summary)} — {_escape(title)}",
            f"DESCRIPTION:{_escape(description)}",
        ]
        if rule:
            lines.append(f"RRULE:{rule}")
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(summary)}",
                  "TRIGGER:-P1D", "END:VALARM", "END:VEVENT"]  # fmt: skip
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
