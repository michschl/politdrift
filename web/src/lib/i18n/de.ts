export const de = {
	'site.name': 'Politdrift',
	'site.claim': 'Gesagt. Gestimmt.',
	'site.lead':
		'Politdrift zeigt, wie Mitglieder des Parlaments tatsächlich abstimmen: verdichtet auf die acht Achsen des Smartspiders, verglichen mit ihrer Fraktion und verfolgt über die Zeit. Jede Zahl ist bis zur einzelnen Abstimmung nachvollziehbar.',
	'site.status': 'Im Aufbau. Die Daten des Nationalrats folgen.',
	'nav.home': 'Start',
	'nav.methodik': 'Methodik',
	'nav.impressum': 'Impressum',
	'nav.datenschutz': 'Datenschutz',
	'nav.main': 'Hauptnavigation',
	'footer.sources': 'Quellen: Parlamentsdienste (parlament.ch) · OpenParlData.ch (CC BY 4.0)',
	'footer.source': 'Quellcode (AGPL-3.0)',
	'footer.datalicense': 'Daten: CC BY 4.0',
	'footer.datastate': 'Datenstand: noch keine Daten publiziert',
	'example.title': 'Beispiel-Spider',
	'example.note':
		'Fiktive Beispieldaten. Das Profil gehört zu keiner realen Person und dient nur zur Darstellung.',
	'example.ist': 'Ist-Profil (Abstimmungen)',
	'example.vergleich': 'Vergleich (Fraktion)',
	'spider.table.caption': 'Werte des Spiders (0–100)',
	'spider.table.axis': 'Achse',
	'spider.nodata': 'zu wenig Daten',
	'axis.aussenpolitik_offen': 'Offene Aussenpolitik',
	'axis.wirtschaft_liberal': 'Liberale Wirtschaftspolitik',
	'axis.finanzen_restriktiv': 'Restriktive Finanzpolitik',
	'axis.law_order': 'Law & Order',
	'axis.migration_restriktiv': 'Restriktive Migrationspolitik',
	'axis.umwelt_ausgebaut': 'Ausgebauter Umweltschutz',
	'axis.sozialstaat_ausgebaut': 'Ausgebauter Sozialstaat',
	'axis.gesellschaft_liberal': 'Liberale Gesellschaft',
	'placeholder.todo': 'Dieser Inhalt folgt vor der Veröffentlichung.'
} as const;

export type MessageKey = keyof typeof de;
