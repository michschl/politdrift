import { json } from '@sveltejs/kit';
import { buildInfo } from '#lib/build-info.ts';

export const prerender = true;

export function GET() {
	return json(buildInfo);
}
