/**
 * Navigation-scoped request cancellation — the portal's copy of the analyst
 * frontend's #1072 mechanism.
 *
 * Leaving a page left its reads running: go Overview → Alerts → Cases quickly and
 * all three pages' calls stay in flight. The browser allows ~6 connections per
 * host, so the page you land on (and its lazily loaded chunk) queues behind the
 * ones you left. Every GET is therefore attached to a controller owned by the
 * current route, and changing route aborts the previous one wholesale. The
 * backend's ClientDisconnectMiddleware then stops working on it too.
 *
 * Unlike the analyst frontend, a caller-supplied `signal` does not opt out: most
 * portal lists own a controller only to cancel a superseded load, and never abort
 * it on unmount — so here the request follows *both* signals.
 *
 * Two rules keep this safe:
 *
 * 1. **GET only.** Aborting a POST/PUT/DELETE client-side does not undo it
 *    server-side; it just hides whether it happened.
 * 2. **`keepOnNavigation` opts a request out** — calls that are not page-scoped
 *    (branding, token refresh, cached lookups, the report poller, file downloads),
 *    where a cancellation would be read as a failure or leave a cache pending.
 */

let controller: AbortController | null = null

/**
 * Abort every navigation-scoped request in flight and open a fresh scope. Called by
 * the router on a path change, before the incoming page's chunk is requested.
 */
export function resetNavigationScope(): void {
	controller?.abort()
	controller = new AbortController()
}

/** Signal for the current route. Created lazily so the first page is covered too. */
export function getNavigationSignal(): AbortSignal {
	if (!controller) {
		controller = new AbortController()
	}
	return controller.signal
}

/** A signal that aborts as soon as any of `signals` does. */
export function anySignal(signals: AbortSignal[]): AbortSignal {
	if (typeof AbortSignal.any === "function") return AbortSignal.any(signals)

	const combined = new AbortController()
	for (const signal of signals) {
		if (signal.aborted) {
			combined.abort(signal.reason)
			break
		}
		signal.addEventListener("abort", () => combined.abort(signal.reason), { once: true })
	}
	return combined.signal
}
