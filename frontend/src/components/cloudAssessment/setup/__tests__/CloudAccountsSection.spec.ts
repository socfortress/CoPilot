import type { VueWrapper } from "@vue/test-utils"
/**
 * The customer's Cloud Accounts section (#1328): setup only. An admin adds and edits accounts; an
 * analyst tests and scans them. The credential is write-only: an edit starts empty and a blank
 * field keeps the stored one.
 */
import type { CloudAccount } from "@/types/cloud-assessment"
import { flushPromises, mount } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { routes } from "@/router/routes"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { account } from "../../__tests__/fixtures"
import { resetCloudAvailability } from "../../useCloudAvailability"
import CloudAccountsSection from "../CloudAccountsSection.vue"

const api = vi.hoisted(() => ({
	availability: vi.fn(),
	getAccounts: vi.fn(),
	createAccount: vi.fn(),
	updateAccount: vi.fn(),
	deleteAccount: vi.fn(),
	testConnection: vi.fn(),
	startScan: vi.fn()
}))
vi.mock("@/api", () => ({ default: { cloudAssessment: api } }))

// Both of the section's modals, rendered in place while shown.
const ModalStub = defineComponent({
	props: { show: Boolean },
	setup(props, { slots }) {
		return () => (props.show ? h("div", { "data-testid": "modal" }, [slots.default?.(), slots.footer?.()]) : null)
	}
})

const ROLE = account()
const KEYS = account({ id: 2, name: "Legacy", auth_method: "access_keys", secret_hint: "…WXYZ" })

let wrapper: VueWrapper | null = null

function current(): VueWrapper {
	if (!wrapper) throw new Error("render() first")
	return wrapper
}

async function render() {
	const router = createRouter({ history: createMemoryHistory(), routes })
	await router.push("/")
	await router.isReady()
	wrapper = mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CloudAccountsSection, { customerCode: "ACME" })) }),
		{ global: { plugins: [router], stubs: { NModal: ModalStub, Modal: ModalStub } }, attachTo: document.body }
	)
	await flushPromises()
	return router
}

function listed(accounts: CloudAccount[], key = true, runner = true) {
	api.getAccounts.mockResolvedValue({ data: { accounts, encryption_key_configured: key, runner_configured: runner } })
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "someone", email: "", role }
}

function buttons(text: string, root: VueWrapper | ReturnType<VueWrapper["find"]> = current()) {
  return root.findAll("button").filter(b => b.text().trim() === text)
}

/** Assume the role with CoPilot's own identity: no keys. */
async function useHostIdentity() {
	const choice = current()
		.findAll("[data-testid=cloud-account-identity] .n-radio")
		.find(radio => radio.text().includes("CoPilot's own AWS identity"))
	if (!choice) throw new Error("the host identity choice is missing")
	await choice.find("input").setValue(true)
}

async function type(testid: string, value: string) {
	await current().find(`[data-testid=${testid}] input, [data-testid=${testid}] textarea`).setValue(value)
}

beforeEach(() => {
	// jsdom has neither matchMedia nor Element.scrollTo; a select's menu uses both.
	Element.prototype.scrollTo ??= () => {}
	window.matchMedia ??= (query: string) =>
		({
			matches: false,
			media: query,
			onchange: null,
			addListener: () => {},
			removeListener: () => {},
			addEventListener: () => {},
			removeEventListener: () => {},
			dispatchEvent: () => false
		}) as MediaQueryList
	setActivePinia(createPinia())
	signInAs(AuthUserRole.Admin)
	resetCloudAvailability()
	for (const fn of Object.values(api)) fn.mockReset()
	api.availability.mockResolvedValue({ data: { prowler_version: "5.13.1", runner_configured: true, runner_reachable: true } })
	listed([ROLE, KEYS])
})

afterEach(() => {
	wrapper?.unmount()
	wrapper = null
	document.body.innerHTML = ""
})

describe("the cloud accounts section", () => {
	it("lists the customer's accounts with what an admin can do to them", async () => {
		await render()
		expect(api.getAccounts).toHaveBeenCalledWith("ACME")
		const card = current().find("[data-testid=cloud-account-1]")
		expect(card.text()).toContain("Production")
		expect(card.text()).toContain("123456789012")
		expect(card.text()).toContain("Daily at 02:00 UTC")
		expect(buttons("Edit", card)).toHaveLength(1)
		expect(buttons("Delete", card)).toHaveLength(1)
		expect(buttons("Role setup", card)).toHaveLength(1)
		expect(buttons("Role setup", current().find("[data-testid=cloud-account-2]"))).toHaveLength(0)
	})

	it("lets an analyst test and scan, never add, edit or delete", async () => {
		signInAs(AuthUserRole.Analyst)
		await render()
		expect(current().text()).toContain("Only administrators can add or change cloud accounts")
		expect(buttons("Add account")).toHaveLength(0)
		expect(buttons("Edit")).toHaveLength(0)
		expect(buttons("Delete")).toHaveLength(0)
		expect(buttons("Test connection")).toHaveLength(2)
		expect(buttons("Scan now")).toHaveLength(2)
	})

	it("says what's missing before credentials can be saved or scans run", async () => {
		listed([], false, false)
		await render()
		expect(current().find("[data-testid=cloud-key-missing]").text()).toContain("CLOUD_ASSESSMENT_ENCRYPTION_KEY")
		expect(current().find("[data-testid=cloud-runner-missing]").text()).toContain("PROWLER_RUNNER_TOKEN")
		expect(current().find<HTMLButtonElement>("[data-testid=cloud-account-add]").element.disabled).toBe(true)
	})

	it("shows a failed connection test's own words, as text", async () => {
		api.testConnection.mockResolvedValue({
			data: {
				ok: false,
				code: "auth_failed",
				error_message: "The cloud refused the credentials: <b>check them</b>.",
				prowler_error: "ClientError",
				account: ROLE
			}
		})
		await render()
		await buttons("Test connection", current().find("[data-testid=cloud-account-1]"))[0]?.trigger("click")
		await flushPromises()
		expect(api.testConnection).toHaveBeenCalledWith("ACME", 1)
		const result = current().find("[data-testid=cloud-test-result-1]")
		expect(result.text()).toContain("The cloud refused the credentials: <b>check them</b>.")
		expect(result.text()).toContain("ClientError")
		expect(result.find("b").exists()).toBe(false)
	})

	it("starts a scan and reads the list again", async () => {
		api.startScan.mockResolvedValue({ data: { message: "Scan queued", scan: { id: 30 } } })
		await render()
		await buttons("Scan now", current().find("[data-testid=cloud-account-1]"))[0]?.trigger("click")
		await flushPromises()
		expect(api.startScan).toHaveBeenCalledWith("ACME", 1)
		expect(api.getAccounts).toHaveBeenCalledTimes(2)
	})

	it("opens an account's scans on the Cloud Security Assessment page", async () => {
		const router = await render()
		const push = vi.spyOn(router, "push")
		await buttons("Open", current().find("[data-testid=cloud-account-1]"))[0]?.trigger("click")
		expect(push).toHaveBeenCalledWith({ name: "CloudSecurityAssessment", query: { customer: "ACME", account: "1" } })
	})
})

describe("the account form", () => {
	it("starts an edit with every credential field empty, and keeps the stored credential when left blank", async () => {
		api.updateAccount.mockResolvedValue({ data: { account: KEYS } })
		await render()
		await buttons("Edit", current().find("[data-testid=cloud-account-2]"))[0]?.trigger("click")
		await flushPromises()
		const keyId = current().find<HTMLInputElement>("[data-testid=cloud-account-access-key-id] input")
		const secret = current().find<HTMLInputElement>("[data-testid=cloud-account-secret-access-key] input")
		expect(keyId.element.value).toBe("")
		expect(secret.element.value).toBe("")
		expect(secret.attributes("placeholder")).toBe("…WXYZ — leave blank to keep")

		await current().find("[data-testid=cloud-account-save]").trigger("click")
		await flushPromises()
		expect(api.updateAccount).toHaveBeenCalledTimes(1)
		const [code, id, payload] = api.updateAccount.mock.calls[0] ?? []
		expect([code, id]).toEqual(["ACME", 2])
		expect(payload).not.toHaveProperty("secret")
		expect(payload).not.toHaveProperty("remove_secret")
	})

	it("refuses to send a form with problems", async () => {
		await render()
		await buttons("Add account")[0]?.trigger("click")
		await flushPromises()
		await current().find("[data-testid=cloud-account-save]").trigger("click")
		await flushPromises()
		expect(api.createAccount).not.toHaveBeenCalled()
		expect(current().text()).toContain("Some fields need a look.")
		expect(current().text()).toContain("Enter a name.")
		expect(current().text()).toContain("Enter the role's ARN")
	})

	it("opens Advanced when one of its fields is the problem", async () => {
		await render()
		await buttons("Add account")[0]?.trigger("click")
		await flushPromises()
		await type("cloud-account-name", "Staging")
		await type("cloud-account-role-arn", "arn:aws:iam::123456789012:role/ProwlerScan")
		await useHostIdentity()
		// A tag typed into "Checks to skip" that isn't a Prowler check id, then Advanced closed again.
		const header = () => current().find("[data-testid=cloud-account-form] .n-collapse-item__header-main")
		await header().trigger("click")
		await flushPromises()
		const checks = current().find("[data-testid=cloud-account-excluded-checks]")
		await checks.find(".n-base-selection").trigger("click")
		const input = checks.find("input")
		await input.setValue("Not A Check")
		await input.trigger("keydown", { key: "Enter", code: "Enter" })
		await flushPromises()
		await header().trigger("click")
		await flushPromises()
		expect(current().find("[data-testid=cloud-account-form] .n-collapse-item--active").exists()).toBe(false)
		await current().find("[data-testid=cloud-account-save]").trigger("click")
		await flushPromises()
		expect(api.createAccount).not.toHaveBeenCalled()
		expect(current().find("[data-testid=cloud-account-form] .n-collapse-item--active").exists()).toBe(true)
		expect(current().text()).toContain('"Not A Check" isn\'t a Prowler check id.')
	})

	it("adds an AWS role account, then shows how to create the role with its External ID", async () => {
		const created = account({ id: 5, name: "Staging", secret_configured: false, secret_hint: null })
		api.createAccount.mockResolvedValue({ data: { account: created } })
		await render()
		await buttons("Add account")[0]?.trigger("click")
		await flushPromises()
		await type("cloud-account-name", "Staging")
		await type("cloud-account-role-arn", "arn:aws:iam::123456789012:role/ProwlerScan")
		await useHostIdentity()
		await current().find("[data-testid=cloud-account-save]").trigger("click")
		await flushPromises()

		expect(api.createAccount).toHaveBeenCalledTimes(1)
		const [code, payload] = api.createAccount.mock.calls[0] ?? []
		expect(code).toBe("ACME")
		expect(payload).toMatchObject({
			name: "Staging",
			provider: "aws",
			auth_method: "role",
			secret: null,
			config: { role_arn: "arn:aws:iam::123456789012:role/ProwlerScan" }
		})
		expect(payload.config).not.toHaveProperty("external_id")
		const setup = current().find("[data-testid=aws-role-setup]")
		expect(setup.find("[data-testid=aws-role-external-id]").text()).toBe(created.external_id)
		expect(setup.text()).toContain("232136659152")
		expect(setup.find("a").attributes("href")).toContain("/blob/5.13.1/permissions/templates/cloudformation/prowler-scan-role.yml")
	})

	it("shows the backend's refusal and keeps the form open", async () => {
		const headers = new AxiosHeaders()
		api.createAccount.mockRejectedValue(
			new AxiosError("x", "ERR", undefined, undefined, {
				status: 409,
				statusText: "",
				data: { message: "An account with that name exists." },
				headers,
				config: { headers }
			})
		)
		await render()
		await buttons("Add account")[0]?.trigger("click")
		await flushPromises()
		await type("cloud-account-name", "Production")
		await type("cloud-account-role-arn", "arn:aws:iam::123456789012:role/ProwlerScan")
		await useHostIdentity()
		await current().find("[data-testid=cloud-account-save]").trigger("click")
		await flushPromises()
		expect(current().find("[data-testid=cloud-account-form-error]").text()).toContain("An account with that name exists.")
		expect(current().find("[data-testid=cloud-account-form]").exists()).toBe(true)
	})
})
