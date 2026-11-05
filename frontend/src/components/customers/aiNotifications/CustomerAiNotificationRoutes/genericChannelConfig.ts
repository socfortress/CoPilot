import type { ChannelConfig, NotificationChannelDescriptor } from "@/types/notifications"

// The `config` of a channel rendered by ChannelConfigFields, built from the
// schema its provider advertises: `cfg` also holds what other channels left
// there, and the backend's schemas use extra="forbid".
//
// An empty field is left out rather than sent as null, so a provider's default
// applies and a field that isn't nullable isn't refused.
export function buildGenericChannelConfig(
	descriptor: NotificationChannelDescriptor,
	values: Record<string, unknown>
): ChannelConfig {
	const config: Record<string, unknown> = {}

	for (const key of Object.keys(descriptor.config_schema?.properties ?? {})) {
		const value = clean(values[key])
		if (value !== undefined && value !== null && value !== "") config[key] = value
	}

	return config as ChannelConfig
}

function clean(value: unknown): unknown {
	if (typeof value === "string") return value.trim()
	if (Array.isArray(value)) return value.map(clean).filter(item => item !== "")
	return value
}
