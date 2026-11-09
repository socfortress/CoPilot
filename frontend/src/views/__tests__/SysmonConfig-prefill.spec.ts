import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import SysmonConfig from "../agents/SysmonConfig.vue"

const sysmonConfig = vi.hoisted(() => ({
	getAll: vi.fn(),
	getDefaultConfig: vi.fn(),
	getConfigContent: vi.fn(),
	uploadConfigFile: vi.fn(),
	deployConfig: vi.fn(),
	saveDefaultConfig: vi.fn()
}))
const customers = vi.hoisted(() => ({ getCustomers: vi.fn() }))
const message = vi.hoisted(() => ({ info: vi.fn(), warning: vi.fn(), error: vi.fn(), success: vi.fn() }))

vi.mock("@/api", () => ({ default: { sysmonConfig, customers } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ isAdmin: true }) }))
vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({ routeCustomer: () => ({ navigate: () => {} }) })
}))
vi.mock("naive-ui", async importOriginal => ({
	...(await importOriginal<typeof import("naive-ui")>()),
	useMessage: () => message,
	useDialog: () => ({ warning: vi.fn() }),
	// "Add new Configuration" picks the customer straight away.
	NDropdown: defineComponent({
		emits: ["select"],
		setup:
			(_, { emit, slots }) =>
			() =>
				h("div", { "data-testid": "new-config", onClick: () => emit("select", "Y") }, slots.default?.())
	})
}))
vi.mock("@/components/common/Icon.vue", () => ({ default: defineComponent({ setup: () => () => h("i") }) }))
vi.mock("@/components/common/SegmentedPage.vue", () => ({
	default: defineComponent({
		setup:
			(_, { slots }) =>
			() =>
				h("div", [slots["sidebar-content"]?.(), slots["main-toolbar"]?.(), slots["main-content"]?.()])
	})
}))
vi.mock("@/components/common/XMLEditor.vue", () => ({
	default: defineComponent({
		props: { modelValue: { type: String, default: "" } },
		setup: (props, { expose }) => {
			expose({ canUndo: () => false, canRedo: () => false, undo: () => {}, redo: () => {} })
			return () => h("pre", { "data-testid": "editor" }, props.modelValue)
		}
	})
}))

const ACME_PATH = "C:\\Program Files\\acme\\chainsaw\\chainsaw.exe"

async function addNewConfiguration(defaultConfig: object) {
	sysmonConfig.getDefaultConfig.mockResolvedValue({ data: { success: true, message: "", ...defaultConfig } })
	const wrapper = mount(SysmonConfig)
	await flushPromises()
	await wrapper.get("[data-testid=new-config]").trigger("click")
	await flushPromises()
	return wrapper
}

/** "Add new Configuration" names an install folder only when the default's placeholder was filled in with it. */
describe("pre-filling a new Sysmon configuration", () => {
	beforeEach(() => {
		vi.clearAllMocks()
		for (const notice of [message.info, message.warning]) notice.mockReturnValue({ destroy: vi.fn() })
		sysmonConfig.getAll.mockResolvedValue({ data: { success: true, customer_codes: [] } })
		customers.getCustomers.mockResolvedValue({
			data: { success: true, customers: [{ customer_code: "Y", customer_name: "Y Corp" }] }
		})
	})

	it("says which install folder the placeholder was filled in with", async () => {
		const wrapper = await addNewConfiguration({
			present: true,
			config_content: "C:\\Program Files\\Y\\chainsaw\\chainsaw.exe",
			rendered_for: "Y",
			placeholders: 2
		})
		expect(sysmonConfig.getDefaultConfig).toHaveBeenCalledWith("Y", expect.anything())
		expect(wrapper.get("[data-testid=editor]").text()).toBe("C:\\Program Files\\Y\\chainsaw\\chainsaw.exe")
		expect(message.info).toHaveBeenCalledWith(
			expect.stringContaining('Install-folder paths use "Y"'),
			expect.anything()
		)
		expect(message.warning).not.toHaveBeenCalled()
	})

	it("warns, and names no install folder, when the default has no placeholder", async () => {
		const wrapper = await addNewConfiguration({
			present: true,
			config_content: ACME_PATH,
			rendered_for: null,
			placeholders: 0
		})
		expect(wrapper.get("[data-testid=editor]").text()).toBe(ACME_PATH)
		expect(message.info).not.toHaveBeenCalled()
		const [[notice, options]] = message.warning.mock.calls
		expect(notice).toContain("has no __INSTALLDIRNAME__ placeholder")
		expect(notice).toContain("Check them before uploading")
		expect(notice).not.toContain("Install-folder paths use")
		expect(options).toMatchObject({ duration: 0, closable: true })
	})

	it("opens the empty skeleton when no default is set", async () => {
		const wrapper = await addNewConfiguration({
			present: false,
			config_content: null,
			rendered_for: null,
			placeholders: 0
		})
		expect(wrapper.get("[data-testid=editor]").text()).toContain("<EventFiltering>")
		expect(message.info).toHaveBeenCalledWith(
			expect.stringContaining("No default Sysmon config is set on this CoPilot"),
			expect.anything()
		)
		expect(message.warning).not.toHaveBeenCalled()
	})
})
