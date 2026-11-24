import type { DefaultSyncApplied, DefaultSyncCheck, DefaultSyncStatus } from "@/types/sysmon-config"
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
	saveDefaultConfig: vi.fn(),
	getDefaultSyncStatus: vi.fn(),
	syncDefaultConfig: vi.fn()
}))
const customers = vi.hoisted(() => ({ getCustomers: vi.fn() }))
const message = vi.hoisted(() => ({ info: vi.fn(), warning: vi.fn(), error: vi.fn(), success: vi.fn() }))
const dialog = vi.hoisted(() => ({ warning: vi.fn() }))
const auth = vi.hoisted(() => ({ isAdmin: true }))

vi.mock("@/api", () => ({ default: { sysmonConfig, customers } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({ routeCustomer: () => ({ navigate: () => {} }) })
}))
vi.mock("naive-ui", async importOriginal => ({
	...(await importOriginal<typeof import("naive-ui")>()),
	useMessage: () => message,
	useDialog: () => dialog
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

const COMMIT = "abcdef1234567890abcdef1234567890abcdef12"

const LAST_CHECK: DefaultSyncCheck = {
	outcome: "up_to_date",
	ok: true,
	message: "This CoPilot's default is SOCFortress release #12 (abcdef1), the latest.",
	mode: "on",
	forced: false,
	checked_at: "2026-11-23T10:00:00Z",
	sequence: null,
	commit: null
}

const APPLIED: DefaultSyncApplied = {
	sequence: 12,
	commit: COMMIT,
	content_sha256: "0".repeat(64),
	content_sha256_crlf: "1".repeat(64),
	key_id: "sysmon-release-1",
	applied_at: "2026-11-20T12:00:00Z",
	created_at: "2026-11-20T11:00:00Z",
	schemaversion: "4.90",
	source: "socfortress-sync",
	service_url: "https://sysmon-sync.socfortress.co"
}

function status(overrides: Partial<DefaultSyncStatus> = {}): DefaultSyncStatus {
	return {
		mode: "on",
		mode_setting: null,
		service_url: "https://sysmon-sync.socfortress.co",
		configured: true,
		trusted_key_ids: ["sysmon-release-1"],
		last_check: LAST_CHECK,
		applied: APPLIED,
		default_present: true,
		local_default_differs: false,
		read_error: null,
		...overrides
	}
}

async function open(current: DefaultSyncStatus) {
	sysmonConfig.getDefaultSyncStatus.mockResolvedValue({ data: { success: true, message: "", status: current } })
	const wrapper = mount(SysmonConfig)
	await flushPromises()
	return wrapper
}

/** One line on the Sysmon Config page says where this CoPilot's default comes from; Sync now checks SOCFortress. */
describe("the SOCFortress default sync line", () => {
	beforeEach(() => {
		vi.clearAllMocks()
		auth.isAdmin = true
		sysmonConfig.getAll.mockResolvedValue({ data: { success: true, customer_codes: [] } })
		customers.getCustomers.mockResolvedValue({ data: { success: true, customers: [] } })
	})

	it("names the SOCFortress release the default is", async () => {
		const wrapper = await open(status())
		const line = wrapper.get("[data-testid=default-sync-line]").text()
		expect(line).toMatch(/^Default: SOCFortress release #12 \(abcdef1\), synced 2026-11-2\d \d\d:\d\d$/)
		expect(wrapper.find("[data-testid=default-sync-detail]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=default-sync-now]").attributes("disabled")).toBeUndefined()
	})

	it("says a default changed here is not updated, and asks before replacing it", async () => {
		const wrapper = await open(
			status({
				local_default_differs: true,
				last_check: { ...LAST_CHECK, outcome: "local_default_differs", ok: false, sequence: 13 }
			})
		)
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toBe(
			"Local default differs from SOCFortress release #13: not updated"
		)

		await wrapper.get("[data-testid=default-sync-now]").trigger("click")
		expect(sysmonConfig.syncDefaultConfig).not.toHaveBeenCalled()
		const [[options]] = dialog.warning.mock.calls
		expect(options.content).toContain("was changed here")

		sysmonConfig.syncDefaultConfig.mockResolvedValue({
			data: {
				success: true,
				message: "",
				result: { outcome: "applied", ok: true, message: "Replaced this CoPilot's default" },
				status: status({ applied: { ...APPLIED, sequence: 13 } })
			}
		})
		options.onPositiveClick()
		await flushPromises()
		expect(sysmonConfig.syncDefaultConfig).toHaveBeenCalledWith(true)
		expect(message.success).toHaveBeenCalledWith("Replaced this CoPilot's default", expect.anything())
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toContain("SOCFortress release #13")
	})

	it("says so when a default was set before sync and differs from the release", async () => {
		const wrapper = await open(
			status({
				applied: null,
				local_default_differs: null,
				last_check: { ...LAST_CHECK, outcome: "local_default_differs", ok: false, sequence: 4 }
			})
		)
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toBe(
			"Local default differs from SOCFortress release #4: not updated"
		)
	})

	it("runs a plain check with Sync now, and shows what it found", async () => {
		const wrapper = await open(status())
		sysmonConfig.syncDefaultConfig.mockResolvedValue({
			data: {
				success: true,
				message: "",
				result: {
					outcome: "network_error",
					ok: false,
					message: "Could not reach the SOCFortress sync service"
				},
				status: status({
					last_check: {
						...LAST_CHECK,
						outcome: "network_error",
						ok: false,
						message: "Could not reach the SOCFortress sync service"
					}
				})
			}
		})
		await wrapper.get("[data-testid=default-sync-now]").trigger("click")
		await flushPromises()
		expect(dialog.warning).not.toHaveBeenCalled()
		expect(sysmonConfig.syncDefaultConfig).toHaveBeenCalledWith(false)
		expect(message.error).toHaveBeenCalledWith("Could not reach the SOCFortress sync service", expect.anything())
		expect(wrapper.get("[data-testid=default-sync-detail]").text()).toBe(
			"Last check: Could not reach the SOCFortress sync service"
		)
	})

	it("says at once when a check is already running", async () => {
		const wrapper = await open(status())
		const detail =
			"A check of SOCFortress's default Sysmon config is already running on this CoPilot (the scheduled one, or another admin's Sync now). Its result shows here once it ends; try again in a minute"
		sysmonConfig.syncDefaultConfig.mockRejectedValue({ name: "AxiosError", response: { status: 409, data: { detail } } })
		await wrapper.get("[data-testid=default-sync-now]").trigger("click")
		await flushPromises()
		expect(message.error).toHaveBeenCalledWith(`${detail}.`)
		expect(wrapper.get("[data-testid=default-sync-now]").attributes("disabled")).toBeUndefined()
	})

	it.each([
		[{ mode: "off" as const }, "SOCFortress default sync off"],
		[{ configured: false, trusted_key_ids: [] }, "SOCFortress default sync not configured"]
	])("disables Sync now when sync is off or not configured", async (overrides, text) => {
		const wrapper = await open(status(overrides))
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toBe(text)
		expect(wrapper.get("[data-testid=default-sync-now]").attributes("disabled")).toBeDefined()
	})

	it("says when the default was never synced, and why", async () => {
		const wrapper = await open(
			status({
				applied: null,
				local_default_differs: null,
				last_check: {
					...LAST_CHECK,
					outcome: "no_license",
					ok: false,
					message: "This CoPilot has no license"
				}
			})
		)
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toBe("Default not synced from SOCFortress yet")
		expect(wrapper.get("[data-testid=default-sync-detail]").text()).toBe("This CoPilot has no license")
	})

	it("asks again after Save as default, so the line shows a default changed here", async () => {
		sysmonConfig.getAll.mockResolvedValue({ data: { success: true, customer_codes: ["acme"] } })
		sysmonConfig.getConfigContent.mockResolvedValue({
			data: { success: true, customer_code: "acme", config_content: "<Sysmon/>" }
		})
		sysmonConfig.saveDefaultConfig.mockResolvedValue({
			data: { success: true, message: "Saved", placeholders: 1, restored: 0 }
		})
		const wrapper = await open(status())
		expect(sysmonConfig.getDefaultSyncStatus).toHaveBeenCalledTimes(1)

		const [customerRow] = wrapper.findAll("div.cursor-pointer").filter(row => row.text() === "acme")
		await customerRow.trigger("click")
		await flushPromises()
		const [saveButton] = wrapper.findAll("button").filter(button => button.text() === "Save as default")
		sysmonConfig.getDefaultSyncStatus.mockResolvedValue({
			data: { success: true, message: "", status: status({ local_default_differs: true }) }
		})
		await saveButton.trigger("click")
		dialog.warning.mock.calls[0][0].onPositiveClick()
		await flushPromises()

		expect(sysmonConfig.saveDefaultConfig).toHaveBeenCalledWith("<Sysmon/>", undefined)
		expect(sysmonConfig.getDefaultSyncStatus).toHaveBeenCalledTimes(2)
		expect(wrapper.get("[data-testid=default-sync-line]").text()).toBe(
			"Local default differs from SOCFortress release #12: not updated"
		)
	})

	it("is not shown to, nor asked for by, anyone but an admin", async () => {
		auth.isAdmin = false
		const wrapper = await open(status())
		expect(sysmonConfig.getDefaultSyncStatus).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=default-sync]").exists()).toBe(false)
	})
})
