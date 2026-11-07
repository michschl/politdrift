import { scaleLinear } from 'd3-scale';
import { curveLinearClosed, lineRadial } from 'd3-shape';
import { AXIS_KEYS, type AxisKey, type AxisProfile } from '../axes';

export const SCORE_MIN = 0;
export const SCORE_MAX = 100;

/** Angle in radians for axis i of n, measured clockwise from 12 o'clock (d3 radial convention). */
export function axisAngle(index: number, count: number = AXIS_KEYS.length): number {
	return (2 * Math.PI * index) / count;
}

/** Cartesian point for a radius at an axis, with the SVG y axis pointing down. */
export function polarToCartesian(angle: number, radius: number): { x: number; y: number } {
	return { x: radius * Math.sin(angle), y: -radius * Math.cos(angle) };
}

export function radiusScale(outerRadius: number) {
	return scaleLinear().domain([SCORE_MIN, SCORE_MAX]).range([0, outerRadius]).clamp(true);
}

/**
 * Closed SVG path for a profile. Missing values (null, "zu wenig Daten") are drawn at the
 * centre so the shape stays closed; the table view shows them explicitly as missing.
 */
export function profilePath(profile: AxisProfile, outerRadius: number): string {
	const r = radiusScale(outerRadius);
	const line = lineRadial<AxisKey>()
		.angle((_, i) => axisAngle(i))
		.radius((key) => r(profile[key] ?? SCORE_MIN))
		.curve(curveLinearClosed);
	return line([...AXIS_KEYS]) ?? '';
}

export function ringPath(value: number, outerRadius: number): string {
	const r = radiusScale(outerRadius)(value);
	return (
		AXIS_KEYS.map((_, i) => {
			const { x, y } = polarToCartesian(axisAngle(i), r);
			return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
		}).join('') + 'Z'
	);
}
