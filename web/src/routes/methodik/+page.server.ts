import { marked } from 'marked';
import source from '../../../../docs/METHODIK.md?raw';
import type { PageServerLoad } from './$types';

// docs/METHODIK.md is the single source for the published method page (KONZEPT 2.3).
// It is rendered once at prerender time; no Markdown parser ships to the browser.
export const load: PageServerLoad = async () => {
	return { html: await marked.parse(source, { gfm: true }) };
};
