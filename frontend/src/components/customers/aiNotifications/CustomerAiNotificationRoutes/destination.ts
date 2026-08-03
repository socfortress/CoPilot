import type { NotificationRoute } from "@/types/notifications"

// Where a route actually delivers, per channel.
//
// `route.destination` is only meaningful for Shuffle — it's the free-form hint
// injected into the app agent's prompt. Every other channel keeps its target in
// the JSON `config` the provider owns (resend: `to`/`cc`, teams: `webhook_url`,
// webhook: `url`), so reading `destination` alone renders an empty line for
// them. One resolver, so the list row and the detail page can't disagree.

export interface RouteDestination {
	/** Field label, e.g. "Recipients" or "POST to". */
	label: string
	/** Configured targets. Empty when the channel resolves them at dispatch time. */
	values: string[]
	/** Shown in place of the values when there are none. */
	note?: string
}

export function describeRouteDestination(route: NotificationRoute): RouteDestination {
	const config = route.config ?? {}

	// 'assignee' resolves the address from the event at dispatch time, so there
	// is no configured destination to show — and showing "none" would be wrong.
	if (route.recipient_mode === "assignee") {
		return {
			label: "Destination",
			values: [],
			note: "resolved from the event's assignee"
		}
	}

	switch (route.channel) {
		case "webhook": {
			const url = (config.url as string) || ""
			return {
				label: `${(config.method as string) || "POST"} to`,
				values: url ? [url] : [],
				note: "no URL configured"
			}
		}
		case "resend": {
			const to = (config.to as string[] | undefined) ?? []
			const cc = (config.cc as string[] | undefined) ?? []
			return {
				label: "Recipients",
				values: [...to, ...cc.map(address => `cc: ${address}`)],
				note: "no recipients configured"
			}
		}
		case "teams": {
			const webhookUrl = (config.webhook_url as string) || ""
			return {
				label: "Teams webhook",
				values: webhookUrl ? [webhookUrl] : [],
				note: "no webhook URL configured"
			}
		}
		default: {
			return {
				label: "Destination",
				values: route.destination ? [route.destination] : [],
				note: "not configured"
			}
		}
	}
}
