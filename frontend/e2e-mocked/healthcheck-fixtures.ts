import type { BrowserContext, Route } from "@playwright/test"

/**
 * A customer's agents for the healthcheck lists (#1291), and a backend that judges them the way
 * CoPilot does (healthchecks/agents/services/unhealthy_delete.py): stale on the list's tool for
 * longer than the threshold, never the Wazuh manager, another customer's agent not found, an agent
 * the other tool still sees kept unless included. Deleting removes them, so the list reads back the
 * change. Times are relative to the moment the mock is installed.
 */

const HOUR = 3_600_000
const DAY = 24 * HOUR

export type Tool = "wazuh" | "velociraptor"

interface MockAgent {
	id: number
	agent_id: string
	hostname: string
	label: string
	os: string
	ip_address: string
	/** Hours since each tool last saw it; null for never (no Velociraptor client). */
	wazuhHours: number
	velociraptorHours: number | null
}

/** ACME's agents. With the list's default filter (1 day) every one but the two fresh is unhealthy. */
export const AGENTS: MockAgent[] = [
	{
		id: 1,
		agent_id: "001",
		hostname: "WIN-DC01",
		label: "dc01",
		os: "Windows",
		ip_address: "10.0.0.11",
		wazuhHours: 2,
		velociraptorHours: 1
	},
	{
		id: 2,
		agent_id: "002",
		hostname: "web-01",
		label: "web01",
		os: "Ubuntu",
		ip_address: "10.0.0.12",
		wazuhHours: 3,
		velociraptorHours: 2
	},
	{
		id: 3,
		agent_id: "003",
		hostname: "LAPTOP-OLD-7",
		label: "laptop7",
		os: "Windows",
		ip_address: "10.0.1.7",
		wazuhHours: 60 * 24,
		velociraptorHours: 58 * 24
	},
	{
		id: 4,
		agent_id: "004",
		hostname: "kiosk-lobby",
		label: "kiosk",
		os: "Windows",
		ip_address: "10.0.1.8",
		wazuhHours: 45 * 24,
		velociraptorHours: null
	},
	{
		id: 5,
		agent_id: "005",
		hostname: "build-agent-02",
		label: "build2",
		os: "Ubuntu",
		ip_address: "10.0.2.2",
		wazuhHours: 40 * 24,
		velociraptorHours: 5
	},
	{
		id: 6,
		agent_id: "006",
		hostname: "FIN-WS-0193",
		label: "fin193",
		os: "Windows",
		ip_address: "10.0.3.93",
		wazuhHours: 3 * 24,
		velociraptorHours: 3 * 24
	},
	{
		id: 7,
		agent_id: "007",
		hostname: "decommissioned-sql-cluster-node-03.corp.acme.example",
		label: "sql3",
		os: "Windows Server",
		ip_address: "10.0.4.3",
		wazuhHours: 400 * 24,
		velociraptorHours: 400 * 24
	},
	...Array.from({ length: 9 }, (_, index) => ({
		id: 10 + index,
		agent_id: String(10 + index).padStart(3, "0"),
		hostname: `vdi-pool-${String(index + 1).padStart(2, "0")}`,
		label: `vdi${index + 1}`,
		os: "Windows",
		ip_address: `10.0.5.${index + 1}`,
		wazuhHours: (35 + index) * 24,
		velociraptorHours: (34 + index) * 24
	}))
]

export interface Recorded {
	previews: { agent_ids: string[]; not_seen_for: { value: number; unit: string } }[]
	deletes: { agent_ids: string[]; not_seen_for: { value: number; unit: string }; include_active_elsewhere: boolean }[]
}

function naive(time: number) {
	return new Date(time).toISOString().replace("Z", "")
}

export async function installHealthcheckMock(
	context: BrowserContext,
	options: { failDeleteFrom?: number; deleteDelayMs?: number; unconfirmed?: string[] } = {}
) {
	const now = Date.now()
	let agents = AGENTS.map(agent => ({ ...agent }))
	const recorded: Recorded = { previews: [], deletes: [] }
	let deleteCalls = 0
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	const lastSeen = (agent: MockAgent, tool: Tool) => {
		const hours = tool === "wazuh" ? agent.wazuhHours : agent.velociraptorHours
		return hours === null ? null : naive(now - hours * HOUR)
	}
	const stale = (agent: MockAgent, tool: Tool, thresholdMs: number) => {
		const hours = tool === "wazuh" ? agent.wazuhHours : agent.velociraptorHours
		return hours === null || hours * HOUR > thresholdMs
	}
	const other = (tool: Tool): Tool => (tool === "wazuh" ? "velociraptor" : "wazuh")
	const judge = (agentId: string, tool: Tool, thresholdMs: number) => {
		const agent = agents.find(item => item.agent_id === agentId)
		if (!agent) return { agent, verdict: "not_found" }
		if (agent.agent_id === "000") return { agent, verdict: "wazuh_manager" }
		if (!stale(agent, tool, thresholdMs)) return { agent, verdict: "seen_recently" }
		if (!stale(agent, other(tool), thresholdMs)) return { agent, verdict: "active_elsewhere" }
		return { agent, verdict: "deletable" }
	}
	const health = (agent: MockAgent) => ({
		id: agent.id,
		os: agent.os,
		label: agent.label,
		wazuh_last_seen: lastSeen(agent, "wazuh"),
		velociraptor_last_seen: lastSeen(agent, "velociraptor"),
		velociraptor_agent_version: agent.velociraptorHours === null ? null : "0.7.4",
		ip_address: agent.ip_address,
		agent_id: agent.agent_id,
		hostname: agent.hostname,
		critical_asset: false,
		velociraptor_id: agent.velociraptorHours === null ? null : `C.${agent.agent_id.padStart(16, "0")}`,
		wazuh_agent_version: "v4.9.0",
		customer_code: "ACME",
		unhealthy_wazuh_agent: null,
		unhealthy_velociraptor_agent: null,
		unhealthy_recent_logs_collected: null
	})
	const thresholdMs = (body: { not_seen_for: { value: number; unit: string } }) =>
		body.not_seen_for.value * (body.not_seen_for.unit === "days" ? DAY : HOUR)

	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: {
						customer_code: "ACME",
						customer_name: "Acme Corp",
						contact_first_name: "A",
						contact_last_name: "B"
					}
				})
			}
			const list = path.match(/^\/customers\/ACME\/agents\/healthcheck\/(wazuh|velociraptor)$/)
			if (list && method === "GET") {
				const tool = list[1] as Tool
				const minutes = Number(url.searchParams.get("minutes") ?? 0)
				const hours = Number(url.searchParams.get("hours") ?? 0)
				const days = Number(url.searchParams.get("days") ?? 0)
				const limit = (minutes + hours * 60 + days * 1440) * 60_000
				const healthy = agents.filter(agent => !stale(agent, tool, limit)).map(health)
				const unhealthy = agents.filter(agent => stale(agent, tool, limit)).map(health)
				return json(route, {
					success: true,
					message: "ok",
					[`healthy_${tool}_agents`]: healthy,
					[`unhealthy_${tool}_agents`]: unhealthy
				})
			}
			const preview = path.match(
				/^\/customers\/ACME\/agents\/healthcheck\/(wazuh|velociraptor)\/delete\/preview$/
			)
			if (preview && method === "POST") {
				const tool = preview[1] as Tool
				const body = route.request().postDataJSON()
				recorded.previews.push(body)
				const limit = thresholdMs(body)
				const judged = (body.agent_ids as string[]).map(agentId => {
					const { agent, verdict } = judge(agentId, tool, limit)
					return agent
						? {
								agent_id: agentId,
								verdict,
								hostname: agent.hostname,
								label: agent.label,
								os: agent.os,
								last_seen: lastSeen(agent, tool),
								other_last_seen: lastSeen(agent, other(tool))
							}
						: {
								agent_id: agentId,
								verdict,
								hostname: null,
								label: null,
								os: null,
								last_seen: null,
								other_last_seen: null
							}
				})
				const counts = { deletable: 0, active_elsewhere: 0, seen_recently: 0, wazuh_manager: 0, not_found: 0 }
				for (const item of judged) counts[item.verdict as keyof typeof counts] += 1
				return json(route, {
					success: true,
					message: "",
					source: tool,
					not_seen_for: body.not_seen_for,
					cutoff: naive(now - limit),
					counts,
					agents: judged
				})
			}
			const remove = path.match(/^\/customers\/ACME\/agents\/healthcheck\/(wazuh|velociraptor)\/delete$/)
			if (remove && method === "POST") {
				const tool = remove[1] as Tool
				const body = route.request().postDataJSON()
				recorded.deletes.push(body)
				deleteCalls += 1
				if (options.deleteDelayMs) await new Promise(resolve => setTimeout(resolve, options.deleteDelayMs))
				if (options.failDeleteFrom && deleteCalls >= options.failDeleteFrom) {
					return json(route, { success: false, message: "Upstream timeout" }, 502)
				}
				const limit = thresholdMs(body)
				const results = (body.agent_ids as string[]).map(agentId => {
					let { agent, verdict } = judge(agentId, tool, limit)
					if (verdict === "active_elsewhere" && body.include_active_elsewhere) verdict = "deletable"
					if (verdict !== "deletable" || !agent) {
						return {
							agent_id: agentId,
							hostname: agent?.hostname ?? null,
							outcome: "skipped",
							reason: verdict,
							unconfirmed: []
						}
					}
					agents = agents.filter(item => item.agent_id !== agentId)
					const unconfirmed = options.unconfirmed?.includes(agentId) ? ["velociraptor"] : []
					return {
						agent_id: agentId,
						hostname: agent.hostname,
						outcome: "deleted",
						reason: null,
						unconfirmed
					}
				})
				const deleted = results.filter(r => r.outcome === "deleted").length
				const skipped = results.filter(r => r.outcome === "skipped").length
				const unconfirmed = results.filter(r => r.outcome === "deleted" && r.unconfirmed.length).length
				return json(route, {
					success: true,
					message: `${deleted} deleted`,
					source: tool,
					not_seen_for: body.not_seen_for,
					requested: results.length,
					deleted,
					skipped,
					failed: 0,
					unconfirmed,
					results
				})
			}
			return route.fallback()
		}
	)
	return { recorded, remaining: () => agents.map(agent => agent.agent_id) }
}
