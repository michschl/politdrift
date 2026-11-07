<script lang="ts">
	import { t } from '#lib';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>{t('nav.methodik')} – {t('site.name')}</title>
</svelte:head>

<!-- Trusted content: rendered at build time from docs/METHODIK.md in this repository. -->
<!-- eslint-disable-next-line svelte/no-at-html-tags -->
<article class="methodik max-w-3xl">{@html data.html}</article>
