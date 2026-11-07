import { de, type MessageKey } from './de';

const dictionaries = { de } as const;
export type Locale = keyof typeof dictionaries;

/** Look up a UI string. Only German exists for now; FR/IT follow (KONZEPT 6.1). */
export function t(key: MessageKey, locale: Locale = 'de'): string {
	return dictionaries[locale][key];
}

export type { MessageKey };
