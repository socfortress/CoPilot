import type { Agent } from "@/types/agents"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AgentVelociraptorIdForm from "../AgentVelociraptorIdForm.vue"

const updateAgent = vi.hoisted(() => vi.fn())
const unpinAgentVelociraptorId = vi.hoisted(() => vi.fn())
const message = vi.hoisted(() => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn() }))

vi.mock("@/api", () => ({ default: { agents: { updateAgent, unpinAgentVelociraptorId } } }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => message
}))
// Icons are not what these tests are about.
vi.mock("@/components/common/Icon.vue", () => ({ default: { props: ["name"], template: "<i :data-icon='name' />" } }))

const AGENT = { agent_id: "001", velociraptor_id: "C.0000000000000001", velociraptor_id_pinned: false } as Agent

function render(agent: Agent = AGENT) {
	return mount(AgentVelociraptorIdForm, { props: { agent, velociraptorId: agent.velociraptor_id } })
}

async function save(wrapper: ReturnType<typeof render>, value: string) {
	await wrapper.get("code").trigger("click")
	await wrapper.get("input").setValue(value)
	await wrapper.get("button").trigger("click")
	await flushPromises()
}

beforeEach(() => {
	updateAgent.mockReset()
	unpinAgentVelociraptorId.mockReset()
	for (const fn of Object.values(message)) fn.mockReset()
})

describe("agentVelociraptorIdForm", () => {
	it("saves, says so, stops loading and shows the id pinned (#1217)", async () => {
		updateAgent.mockResolvedValue({ data: { success: true, message: "ok" } })
		const wrapper = render()
		await save(wrapper, "C.1234567890abcdef")

		expect(updateAgent).toHaveBeenCalledWith("001", { velociraptor_id: "C.1234567890abcdef" })
		expect(message.success).toHaveBeenCalledWith("Velociraptor ID updated successfully")
		expect(wrapper.emitted("updated")).toEqual([["C.1234567890abcdef"]])
		expect(wrapper.emitted("update:velociraptorId")).toEqual([["C.1234567890abcdef"]])
		expect(wrapper.find("input").exists()).toBe(false)
		expect(wrapper.get("[data-icon]").attributes("data-icon")).toBe("uil:edit-alt")
		expect(wrapper.text()).toContain("Pinned")
	})

	it("reports a refused save and lets the user try again", async () => {
		updateAgent.mockRejectedValue({ response: { status: 400, data: { success: false, message: "Invalid Velociraptor client id" } } })
		const wrapper = render()
		await save(wrapper, "not-an-id")

		expect(message.error).toHaveBeenCalledWith(expect.stringContaining("Invalid Velociraptor client id"))
		expect(message.success).not.toHaveBeenCalled()
		expect(wrapper.emitted("updated")).toBeUndefined()
		expect(wrapper.get("input").attributes("disabled")).toBeUndefined()
	})

	it("says so when the id is unpinned", async () => {
		unpinAgentVelociraptorId.mockResolvedValue({ data: { success: true, message: "ok" } })
		const wrapper = render({ ...AGENT, velociraptor_id_pinned: true })
		await wrapper.get(".n-tag__close, .n-base-close").trigger("click")
		await flushPromises()

		expect(unpinAgentVelociraptorId).toHaveBeenCalledWith("001")
		expect(message.success).toHaveBeenCalledWith(expect.stringContaining("unpinned"))
		expect(wrapper.text()).not.toContain("Pinned")
	})
})
