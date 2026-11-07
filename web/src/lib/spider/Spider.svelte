<script lang="ts">
	import { AXES, type AxisProfile } from '../axes';
	import { t } from '../i18n';
	import { axisAngle, polarToCartesian, profilePath, ringPath } from './geometry';

	interface Props {
		profile: AxisProfile;
		comparison?: AxisProfile;
		title: string;
		size?: number;
	}

	let { profile, comparison, title, size = 520 }: Props = $props();

	const outer = 120;
	const labelRadius = outer + 14;
	const rings = [25, 50, 75, 100];
	const id = $props.id();

	function anchor(angle: number): 'start' | 'middle' | 'end' {
		const x = Math.sin(angle);
		if (Math.abs(x) < 0.1) return 'middle';
		return x > 0 ? 'start' : 'end';
	}

	/** Split long labels onto two lines at the first space ("Restriktive / Finanzpolitik"). */
	function lines(label: string): string[] {
		const i = label.indexOf(' ');
		return label.length > 14 && i > 0 ? [label.slice(0, i), label.slice(i + 1)] : [label];
	}

	const fmt = (v: number | null) => (v === null ? t('spider.nodata') : String(Math.round(v)));
</script>

<figure class="flex flex-col items-center gap-4">
	<svg
		viewBox="-270 -160 540 320"
		width={size}
		class="h-auto max-w-full"
		role="img"
		aria-labelledby="{id}-title"
	>
		<title id="{id}-title">{title}</title>
		<g class="text-slate-300 dark:text-slate-600">
			{#each rings as ring (ring)}
				<path d={ringPath(ring, outer)} fill="none" stroke="currentColor" stroke-width="1" />
			{/each}
			{#each AXES as axis, i (axis.key)}
				{@const end = polarToCartesian(axisAngle(i), outer)}
				<line x1="0" y1="0" x2={end.x} y2={end.y} stroke="currentColor" stroke-width="1" />
			{/each}
		</g>
		{#if comparison}
			<path
				d={profilePath(comparison, outer)}
				fill="none"
				stroke="#E69F00"
				stroke-width="2"
				stroke-dasharray="6 4"
			/>
		{/if}
		<path
			d={profilePath(profile, outer)}
			fill="#0072B2"
			fill-opacity="0.3"
			stroke="#0072B2"
			stroke-width="2.5"
		/>
		<g class="fill-slate-700 text-[11px] dark:fill-slate-200">
			{#each AXES as axis, i (axis.key)}
				{@const a = axisAngle(i)}
				{@const p = polarToCartesian(a, labelRadius)}
				{@const parts = lines(t(axis.labelKey))}
				{@const dy0 =
					Math.cos(a) > 0.5
						? -(parts.length - 1) * 1.15
						: Math.cos(a) < -0.5
							? 0
							: -(parts.length - 1) * 0.575}
				<text x={p.x} y={p.y} text-anchor={anchor(a)} dominant-baseline="middle">
					{#each parts as part, j (j)}
						<tspan x={p.x} dy="{j === 0 ? dy0 : 1.15}em">{part}</tspan>
					{/each}
				</text>
			{/each}
		</g>
	</svg>

	<table class="w-full max-w-md text-left text-sm">
		<caption class="mb-2 text-left font-semibold">{t('spider.table.caption')}</caption>
		<thead>
			<tr class="border-b border-slate-300 dark:border-slate-600">
				<th scope="col" class="py-1 pr-2">{t('spider.table.axis')}</th>
				<th scope="col" class="py-1 pr-2 text-right">{t('example.ist')}</th>
				{#if comparison}
					<th scope="col" class="py-1 text-right">{t('example.vergleich')}</th>
				{/if}
			</tr>
		</thead>
		<tbody>
			{#each AXES as axis (axis.key)}
				<tr class="border-b border-slate-200 dark:border-slate-700">
					<th scope="row" class="py-1 pr-2 font-normal">{t(axis.labelKey)}</th>
					<td class="py-1 pr-2 text-right tabular-nums">{fmt(profile[axis.key])}</td>
					{#if comparison}
						<td class="py-1 text-right tabular-nums">{fmt(comparison[axis.key])}</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>
</figure>
