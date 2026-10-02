import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent, h } from "vue"
import UbaDeployGuide from "../UbaDeployGuide.vue"

// The real CodeSource highlights asynchronously; the commands are what matters here.
const CodeSource = defineComponent({ props: { code: { type: String, required: true } }, setup: p => () => h("pre", p.code) })

function render() {
	return mount(UbaDeployGuide, { global: { stubs: { CodeSource } } })
}

describe("ubaDeployGuide", () => {
	it("creates CoPilot's key for every customer with the scope setup needs", () => {
		const text = render().text()
		expect(text).toContain("uba-admin api-keys create --name copilot --scope admin --tenants '*'")
		expect(text).toContain("Platform → Connectors → SOCFortress UBA")
	})

	it("configures what CoPilot's setup and the alert loop rely on, and no customers", () => {
		const code = render()
			.findAll("pre")
			.map(w => w.text())
			.join("\n")
		for (const name of [
			"UBA_PROVISION_FEED_HOST",
			"UBA_PROVISION_ALERTS_BIND",
			"UBA_GRAYLOG_GELF_HOST",
			"UBA_INDEXER__URL",
			"UBA_SECRET_KEY",
			"UBA_COPILOT_URL"
		]) {
			expect(code).toContain(`${name}=`)
		}
		expect(code).toContain("UBA_BOOTSTRAP_TENANTS=[]")
		// The API's published address is the connector URL the guide tells admins to enter.
		expect(code).toContain("UBA_API_PUBLISH=172.17.0.1:8010")
		expect(render().text()).toContain("URL http://172.17.0.1:8010")
	})

	it("reads as prose: no space before punctuation", () => {
		const prose = render()
			.findAll("p")
			.map(w => w.text())
			.join(" ")
		expect(prose).not.toMatch(/\s[,.:;)]/)
	})
})
