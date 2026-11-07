export const prerender = true;

export function GET() {
	return new Response('ok\n', { headers: { 'content-type': 'text/plain; charset=utf-8' } });
}
