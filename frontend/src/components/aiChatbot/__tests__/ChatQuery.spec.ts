/**
 * Which server the AI Chatbot asks.
 *
 * The chatbot keeps the chosen server in localStorage. Its local servers (wazuh-indexer,
 * wazuh-manager, copilot, velociraptor) went away with the copilot-mcp container, so a stored
 * choice can name a server the backend no longer lists. The chatbot then picks the first listed
 * server, and never announces the stale one, which would ask for its example questions and fail.
 */

import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import ChatQuery from "../ChatQuery.vue"

const STORAGE_KEY = "ai-chatbot-selected-server"

const servers = [
	{ name: "Threat Intel", value: "threat-intel", description: "Threat intelligence lookups", capabilities: [] },
	{ name: "Cyber News", value: "cyber-news", description: "Cyber threat news", capabilities: [] }
]

vi.mock("@/api", () => ({
	default: {
		copilotMCP: {
			getAvailableServers: async () => ({ data: { success: true, message: "ok", servers } })
		}
	}
}))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn() })
}))

async function render() {
	const wrapper = mount(ChatQuery, { global: { stubs: { Icon: true } } })
	await flushPromises()
	return wrapper
}

describe("the AI Chatbot's server", () => {
	beforeEach(() => {
		localStorage.clear()
	})

	it("replaces a stored server the backend no longer lists with the first listed one", async () => {
		localStorage.setItem(STORAGE_KEY, "wazuh-indexer")

		const wrapper = await render()

		expect(wrapper.emitted("select-server")).toEqual([["threat-intel"]])
		expect(localStorage.getItem(STORAGE_KEY)).toBe("threat-intel")
	})

	it("keeps a stored server that is still listed", async () => {
		localStorage.setItem(STORAGE_KEY, "cyber-news")

		const wrapper = await render()

		expect(wrapper.emitted("select-server")).toEqual([["cyber-news"]])
	})

	it("picks the first listed server when none was stored", async () => {
		const wrapper = await render()

		expect(wrapper.emitted("select-server")).toEqual([["threat-intel"]])
	})
})
