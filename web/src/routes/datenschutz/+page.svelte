<script lang="ts">
	import { t } from '#lib';
</script>

<svelte:head>
	<title>{t('nav.datenschutz')} – {t('site.name')}</title>
</svelte:head>

<h1 class="text-3xl font-bold">{t('nav.datenschutz')}</h1>
<p class="mt-4">{t('placeholder.todo')}</p>
<p class="mt-4 max-w-2xl">
	Politdrift setzt keine Cookies und verwendet keine Tracker oder Analysedienste. Die Website lädt
	keine Inhalte von Drittanbietern.
</p>
