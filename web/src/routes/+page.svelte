<script lang="ts">
	import { t } from '#lib';
	import Spider from '#lib/spider/Spider.svelte';
	import { exampleIst, exampleVergleich } from '#lib/example.ts';
</script>

<svelte:head>
	<title>{t('site.name')} – {t('site.claim')}</title>
	<meta name="description" content={t('site.lead')} />
</svelte:head>

<section class="space-y-4">
	<h1 class="text-4xl font-bold tracking-tight sm:text-5xl">
		{t('site.name')} <span class="block text-slate-600 dark:text-slate-400">{t('site.claim')}</span>
	</h1>
	<p class="max-w-2xl text-lg">{t('site.lead')}</p>
	<p class="text-sm font-semibold">{t('site.status')}</p>
</section>

<section class="mt-10" aria-labelledby="example-heading">
	<h2 id="example-heading" class="text-2xl font-semibold">{t('example.title')}</h2>
	<p class="mt-1 text-sm text-slate-700 dark:text-slate-300">{t('example.note')}</p>
	<ul class="mt-3 flex flex-wrap gap-4 text-sm">
		<li class="flex items-center gap-2">
			<svg width="24" height="12" aria-hidden="true"
				><rect
					width="24"
					height="12"
					fill="#0072B2"
					fill-opacity="0.3"
					stroke="#0072B2"
					stroke-width="2"
				/></svg
			>{t('example.ist')}
		</li>
		<li class="flex items-center gap-2">
			<svg width="24" height="12" aria-hidden="true"
				><line
					x1="0"
					y1="6"
					x2="24"
					y2="6"
					stroke="#E69F00"
					stroke-width="2"
					stroke-dasharray="6 4"
				/></svg
			>{t('example.vergleich')}
		</li>
	</ul>
	<div class="mt-6">
		<Spider
			profile={exampleIst}
			comparison={exampleVergleich}
			title="{t('example.title')}: {t('example.ist')} und {t('example.vergleich')}"
		/>
	</div>
</section>
