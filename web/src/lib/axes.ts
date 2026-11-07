/**
 * The eight Smartspider axes in display order: 12 o'clock first, then clockwise.
 * Must stay in sync with pipeline/politdrift/axes.py (see docs/METHODIK.md).
 */
export const AXIS_KEYS = [
	'aussenpolitik_offen',
	'wirtschaft_liberal',
	'finanzen_restriktiv',
	'law_order',
	'migration_restriktiv',
	'umwelt_ausgebaut',
	'sozialstaat_ausgebaut',
	'gesellschaft_liberal'
] as const;

export type AxisKey = (typeof AXIS_KEYS)[number];

export type AxisProfile = Record<AxisKey, number | null>;

export const AXES: readonly { key: AxisKey; labelKey: `axis.${AxisKey}` }[] = AXIS_KEYS.map(
	(key) => ({ key, labelKey: `axis.${key}` as const })
);
