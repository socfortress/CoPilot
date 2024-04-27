import { useRouter } from "vue-router"

export function useGoto() {
	const router = useRouter()

	function gotoCustomer(code?: string | number | { [key: string]: any }) {
		if (code) {
			router.push({ name: "Customers", query: { code: code.toString() } })
		} else {
			router.push({ name: "Customers" })
		}
	}

	function gotoAgent(agentId?: string | number) {
		if (agentId) {
			router.push({ name: "Agent", params: { id: agentId.toString() } })
		} else {
			router.push({ name: "Agents" })
		}
	}

	function gotoIndex(indexName?: string) {
		if (indexName) {
			router.push({ name: "Indices", query: { index_name: indexName } })
		} else {
			router.push({ name: "Indices" })
		}
	}

	function gotoLicense() {
		router.push({ name: "License" })
	}

	function gotoHealthcheck() {
		router.push({ name: "Healthcheck" })
	}

	function gotoGraylogMetrics() {
		router.push({ name: "Graylog-Metrics" })
	}

	function gotoGraylogManagement(tabName?: "messages" | "alerts" | "events" | "streams" | "provisioning" | "inputs") {
		router.push({ name: "Graylog-Management", hash: tabName ? `#${tabName}` : undefined })
	}

	return {
		gotoCustomer,
		gotoAgent,
		gotoIndex,
		gotoLicense,
		gotoHealthcheck,
		gotoGraylogMetrics,
		gotoGraylogManagement
	}
}
