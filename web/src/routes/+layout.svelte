<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { t } from '#lib';
	import { resolve } from '$app/paths';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="mx-auto flex min-h-screen max-w-4xl flex-col px-4">
	<header class="flex flex-wrap items-baseline justify-between gap-2 py-6">
		<a href={resolve('/')} class="text-xl font-bold tracking-tight">{t('site.name')}</a>
		<nav aria-label={t('nav.main')}>
			<ul class="flex gap-4 text-sm">
				<li>
					<a class="underline-offset-4 hover:underline" href={resolve('/methodik')}
						>{t('nav.methodik')}</a
					>
				</li>
			</ul>
		</nav>
	</header>

	<main id="main" class="flex-1">
		{@render children()}
	</main>

	<footer
		class="mt-12 border-t border-slate-300 py-6 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300"
	>
		<p>{t('footer.sources')}</p>
		<p>{t('footer.datastate')}</p>
		<ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1">
			<li>
				<a class="underline underline-offset-4" href={resolve('/impressum')}>{t('nav.impressum')}</a
				>
			</li>
			<li>
				<a class="underline underline-offset-4" href={resolve('/datenschutz')}
					>{t('nav.datenschutz')}</a
				>
			</li>
			<li>
				<a class="underline underline-offset-4" href="https://github.com/michschl/politdrift"
					>{t('footer.source')}</a
				>
			</li>
			<li>
				<a
					class="underline underline-offset-4"
					href="https://github.com/michschl/politdrift/blob/main/data/LICENSE"
					>{t('footer.datalicense')}</a
				>
			</li>
		</ul>
	</footer>
</div>
