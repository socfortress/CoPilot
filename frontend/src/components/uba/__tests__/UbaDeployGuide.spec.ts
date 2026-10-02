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

	it("names what to fill in .env for UBA on its own VM", () => {
		const code = render()
			.findAll("pre")
			.map(w => w.text())
			.join("\n")
		for (const name of ["UBA_PROVISION_FEED_HOST=<uba-ip>", "UBA_GRAYLOG_GELF_HOST=<graylog-ip>", "UBA_INDEXER__URL", "UBA_SECRET_KEY", "UBA_COPILOT_URL"]) {
			expect(code).toContain(name)
		}
		expect(code).not.toContain("host.docker.internal")
		expect(render().text()).toContain("URL http://<uba-ip>:8010")
	})

	it("deploys from the public repository, not from source", () => {
		const code = render()
			.findAll("pre")
			.map(w => w.text())
			.join("\n")
		expect(code).toContain("git clone https://github.com/socfortress/socfortress-uba-deploy.git /opt/socfortress-uba")
		expect(code).toContain("cp .env.example .env")
		expect(code).not.toContain("--build")
	})

	it("reads as prose: no space before punctuation", () => {
		const prose = render()
			.findAll("p")
			.map(w => w.text())
			.join(" ")
		expect(prose).not.toMatch(/\s[,.:;)](?!env)/) // a filename like .env is not punctuation
	})
})
