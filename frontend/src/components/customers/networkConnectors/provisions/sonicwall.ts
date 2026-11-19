import type { SonicwallProvision } from "@/api/endpoints/network-connectors"

/**
 * How the customer's SonicWall sends its syslog, which decides the Graylog input deployed for it.
 * The backend's `SonicwallProtocol` (`app/stack_provisioning/graylog/schema/sonicwall.py`).
 */
export type SonicwallProtocol = "tls" | "udp"

export const SONICWALL_PROTOCOL_HINTS: Record<SonicwallProtocol, string> = {
	tls: "Syslog over TCP with TLS, from a syslog-ng collector in front of the firewall. Needs the connector's TLS_CERT_FILE and TLS_KEY_FILE.",
	udp: "Syslog over UDP, sent by the firewall straight to the SIEM stack on the connector's SYSLOG_PORT. TLS_CERT_FILE and TLS_KEY_FILE are not used."
}

export interface SonicwallDeployOptions {
	protocol: SonicwallProtocol
	hot_data_retention: number
	index_replicas: number
}

/** The deploy request: exactly one transport flag is set. */
export function toSonicwallProvision(options: SonicwallDeployOptions): SonicwallProvision {
	return {
		tls_enabled: options.protocol === "tls",
		udp_enabled: options.protocol === "udp",
		hot_data_retention: options.hot_data_retention,
		index_replicas: options.index_replicas
	}
}
