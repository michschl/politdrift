"""The eight Smartspider axes (KONZEPT 2.1).

Order is the display order: 12 o'clock first, then clockwise. Keep in sync with web/src/lib/axes.ts.
"""

from enum import StrEnum


class Axis(StrEnum):
    AUSSENPOLITIK_OFFEN = "aussenpolitik_offen"
    WIRTSCHAFT_LIBERAL = "wirtschaft_liberal"
    FINANZEN_RESTRIKTIV = "finanzen_restriktiv"
    LAW_ORDER = "law_order"
    MIGRATION_RESTRIKTIV = "migration_restriktiv"
    UMWELT_AUSGEBAUT = "umwelt_ausgebaut"
    SOZIALSTAAT_AUSGEBAUT = "sozialstaat_ausgebaut"
    GESELLSCHAFT_LIBERAL = "gesellschaft_liberal"


AXIS_ORDER: tuple[Axis, ...] = tuple(Axis)
