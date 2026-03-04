// BLUEPRINT: api-client-auth
// STRUCTURAL: SSR guard, timeout/AbortSignal composition, typed error class, generic response, token injection shape
// ILLUSTRATIVE: API_BASE, API_TIMEOUT_MS, token source (replace with your auth context)

// STRUCTURAL: named error class preserves status and detail for typed catch handling
export class ApiError extends Error {
	constructor(
		public readonly status: number,
		public readonly title: string,
		public readonly detail: string
	) {
		super(`${title}: ${detail}`);
		this.name = 'ApiError';
	}
}

const API_BASE = '/api'; // ILLUSTRATIVE: adjust per environment
const API_TIMEOUT_MS = 30_000; // STRUCTURAL: always bound async calls

// STRUCTURAL: SSR guard — browser APIs unavailable during server-side render
function buildSignal(callerSignal?: AbortSignal): AbortSignal | undefined {
	const supportsComposedAbort =
		typeof window !== 'undefined' &&
		typeof AbortSignal !== 'undefined' &&
		typeof AbortSignal.timeout === 'function' &&
		typeof AbortSignal.any === 'function';

	if (!supportsComposedAbort) return callerSignal;
	if (callerSignal) return AbortSignal.any([callerSignal, AbortSignal.timeout(API_TIMEOUT_MS)]);
	return AbortSignal.timeout(API_TIMEOUT_MS);
}

// STRUCTURAL: token injected at call boundary — never stored in module scope
// ILLUSTRATIVE: replace getAuthToken() with your session/store lookup
export async function apiFetch<T>(
	path: string,
	options: RequestInit = {},
	getAuthToken?: () => string | null
): Promise<T> {
	const signal = buildSignal(options.signal ?? undefined);

	const authHeader: Record<string, string> = {};
	const token = getAuthToken?.();
	if (token) {
		authHeader['Authorization'] = `Bearer ${token}`; // STRUCTURAL: header, never query param
	}

	const request: RequestInit = {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...authHeader,
			...options.headers
		},
		signal
	};

	const response = await fetch(`${API_BASE}${path}`, request);

	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		throw new ApiError(
			response.status,
			body.detail?.title ?? 'Request Failed',
			body.detail?.detail ?? response.statusText
		);
	}

	return response.json().catch(() => {
		throw new ApiError(response.status, 'Parse Error', 'Response body was not valid JSON');
	}) as Promise<T>;
}
