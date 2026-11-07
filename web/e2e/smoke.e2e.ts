import { expect, test, type Page } from '@playwright/test';

/**
 * Known, accepted CSP report: SvelteKit's route announcer has an inline style attribute that
 * our CSP blocks on purpose; layout.css restyles it (ADR 0003). Matched by its exact hash so
 * any other inline style still fails the test.
 */
const ANNOUNCER_STYLE_HASH = 'sha256-S8qMpvofolR8Mpjy4kQvEm7m1q8clzU4dfDH0AmvZjo=';

/** Collect CSP violations and console errors so a too-strict or too-loose CSP fails the test. */
function watch(page: Page) {
	const problems: string[] = [];
	page.on('console', (msg) => {
		if (msg.type() !== 'error') return;
		if (msg.text().includes(ANNOUNCER_STYLE_HASH)) return;
		problems.push(msg.text());
	});
	page.on('pageerror', (err) => problems.push(err.message));
	return problems;
}

test('landing page shows claim and example spider with table', async ({ page }) => {
	const problems = watch(page);
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1 })).toContainText('Gesagt. Gestimmt.');
	await expect(page.getByRole('img', { name: /Beispiel-Spider/ })).toBeVisible();
	await expect(page.getByRole('rowheader')).toHaveCount(8);
	await expect(page.getByRole('rowheader').first()).toHaveText('Offene Aussenpolitik');
	expect(problems).toEqual([]);
});

test('CSP meta tag is present and free of unsafe-*', async ({ page }) => {
	await page.goto('/');
	const csp = await page
		.locator('meta[http-equiv="content-security-policy"]')
		.getAttribute('content');
	expect(csp).toContain("script-src 'self'");
	expect(csp).not.toContain('unsafe');
});

for (const path of ['/methodik', '/impressum', '/datenschutz']) {
	test(`${path} renders without errors`, async ({ page }) => {
		const problems = watch(page);
		await page.goto(path);
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		expect(problems).toEqual([]);
	});
}

test('client-side navigation works under the CSP', async ({ page }) => {
	const problems = watch(page);
	await page.goto('/');
	await page.getByRole('link', { name: 'Methodik' }).click();
	await expect(page).toHaveURL(/\/methodik$/);
	await expect(page.getByRole('heading', { level: 1 })).toContainText('Methodik');
	expect(problems).toEqual([]);
});

test('route announcer stays visually hidden despite the blocked inline style', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Methodik' }).click();
	const box = await page.locator('#svelte-announcer').boundingBox();
	expect(box?.width ?? 0).toBeLessThanOrEqual(1);
});

test('healthz and version.json', async ({ request }) => {
	const health = await request.get('/healthz');
	expect(await health.text()).toBe('ok\n');
	const version = await (await request.get('/version.json')).json();
	expect(version).toHaveProperty('sha');
	expect(version).toHaveProperty('built_at');
});
