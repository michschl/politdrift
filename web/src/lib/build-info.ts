// Evaluated at build/prerender time only. PUBLIC_BUILD_SHA is set by CI (cicd.yml).
const sha = (process.env.PUBLIC_BUILD_SHA ?? 'dev').slice(0, 7);

export const buildInfo = {
	sha,
	built_at: new Date().toISOString()
} as const;
