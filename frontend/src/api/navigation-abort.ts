/**
 * Navigation-scoped request cancellation (#1072).
 *
 * Per-component AbortControllers only help the ~40 components that bother to
 * create one; the other ~340 fire their requests and forget them, so leaving a
 * page left its loads running. Rather than wiring a controller into every
 * component — hundreds of edits, and one missed component silently reintroduces
 * the bug — every GET is attached to a controller owned by the *current route*.
 * Changing route aborts the previous one wholesale.
 *
 * Three rules keep this safe:
 *
 * 1. **GET only.** Aborting a POST/PUT/DELETE client-side does not undo it
 *    server-side; it just hides whether it happened. Mutations always run to
 *    completion.
 * 2. **A caller-supplied `signal` always wins.** A component that manages its
 *    own controller keeps its exact current behaviour, including its
 *    `axios.isCancel` handling and its `.finally` cleanup.
 * 3. **`keepOnNavigation` opts a request out** — for calls that are not
 *    view-scoped (token refresh, licence gating, bootstrap lookups) where a
 *    cancellation would be read as a failure and change what the UI shows.
 */

let controller: AbortController | null = null

/**
 * Abort every navigation-scoped request in flight and open a fresh scope.
 *
 * Called from the router once a navigation is confirmed and before the incoming
 * page's components mount, so it only ever cancels the outgoing page's work.
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
