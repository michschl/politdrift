import { describe, expect, it } from 'vitest';
import { AXIS_KEYS, type AxisProfile } from '../axes';
import { axisAngle, polarToCartesian, profilePath, radiusScale } from './geometry';

const full = (v: number): AxisProfile =>
	Object.fromEntries(AXIS_KEYS.map((k) => [k, v])) as AxisProfile;

describe('axis order', () => {
	it('has eight axes, starting with aussenpolitik_offen at 12 o clock', () => {
		expect(AXIS_KEYS).toHaveLength(8);
		expect(AXIS_KEYS[0]).toBe('aussenpolitik_offen');
		const top = polarToCartesian(axisAngle(0), 100);
		expect(top.x).toBeCloseTo(0);
		expect(top.y).toBeCloseTo(-100);
	});

	it('runs clockwise: the second axis lies to the upper right', () => {
		const p = polarToCartesian(axisAngle(1), 100);
		expect(p.x).toBeGreaterThan(0);
		expect(p.y).toBeLessThan(0);
	});

	it('places the fifth axis at 6 o clock', () => {
		const p = polarToCartesian(axisAngle(4), 100);
		expect(p.x).toBeCloseTo(0);
		expect(p.y).toBeCloseTo(100);
	});
});

describe('radius scale', () => {
	it('maps 0..100 onto 0..outer and clamps', () => {
		const r = radiusScale(120);
		expect(r(0)).toBe(0);
		expect(r(50)).toBe(60);
		expect(r(100)).toBe(120);
		expect(r(140)).toBe(120);
	});
});

describe('profilePath', () => {
	it('produces a closed path with one vertex per axis', () => {
		const d = profilePath(full(50), 100);
		expect(d.startsWith('M')).toBe(true);
		expect(d.endsWith('Z')).toBe(true);
		expect(d.match(/L/g)).toHaveLength(7);
	});

	it('draws missing values at the centre', () => {
		const p = { ...full(100), aussenpolitik_offen: null };
		expect(profilePath(p, 100).startsWith('M0,0')).toBe(true);
	});
});
