import type { SonicWallModel } from "../provisions/SonicwallForm.vue"
import { mount } from "@vue/test-utils"
import { NRadioButton } from "naive-ui"
import { describe, expect, it } from "vitest"
import { nextTick, ref } from "vue"
import { SONICWALL_PROTOCOL_HINTS, toSonicwallProvision } from "../provisions/sonicwall"
import SonicwallForm from "../provisions/SonicwallForm.vue"
import { authKeyPlaceholder, isOptionalAuthKey } from "../utils"

describe("the SonicWall deploy request", () => {
	it("sets exactly the chosen transport", () => {
		expect(toSonicwallProvision({ protocol: "udp", hot_data_retention: 30, index_replicas: 1 })).toEqual({
			tls_enabled: false,
			udp_enabled: true,
			hot_data_retention: 30,
			index_replicas: 1
		})
		expect(toSonicwallProvision({ protocol: "tls", hot_data_retention: 7, index_replicas: 0 })).toEqual({
			tls_enabled: true,
			udp_enabled: false,
			hot_data_retention: 7,
			index_replicas: 0
		})
	})
})

describe("the network connector keys a customer may leave empty", () => {
	it("are SonicWall's TLS files, which a UDP deploy never reads", () => {
		expect(isOptionalAuthKey("Sonicwall", "TLS_CERT_FILE")).toBe(true)
		expect(isOptionalAuthKey("Sonicwall", "TLS_KEY_FILE")).toBe(true)
		expect(isOptionalAuthKey("Sonicwall", "SYSLOG_PORT")).toBe(false)
	})

	it("stay required everywhere else", () => {
		// SentinelOne only has a TLS input, so its files are always needed.
		expect(isOptionalAuthKey("Sentinelone", "TLS_CERT_FILE")).toBe(false)
		expect(isOptionalAuthKey("Fortinet", "SYSLOG_PORT")).toBe(false)
	})

	it("say why they may be empty", () => {
		expect(authKeyPlaceholder("Sonicwall", "TLS_KEY_FILE")).toContain("UDP")
		expect(authKeyPlaceholder("Sonicwall", "SYSLOG_PORT")).toBe("Input SYSLOG_PORT...")
		expect(authKeyPlaceholder("Fortinet", "SYSLOG_PORT")).toBe("Input SYSLOG_PORT...")
	})
})

describe("the SonicWall deploy form", () => {
	function mountForm(protocol: SonicWallModel["protocol"]) {
		const options = ref<SonicWallModel>({ protocol, hot_data_retention: 1, index_replicas: 0 })
		const wrapper = mount(SonicwallForm, {
			props: {
				options: options.value,
				"onUpdate:options": (value: SonicWallModel) => (options.value = value)
			}
		})
		return { wrapper, options }
	}

	it("offers TLS and UDP", () => {
		const { wrapper } = mountForm("tls")

		expect(wrapper.findAllComponents(NRadioButton).map(button => button.props("value"))).toEqual(["tls", "udp"])
	})

	it("explains the chosen transport", async () => {
		const { wrapper, options } = mountForm("tls")
		const hint = () => wrapper.get("[data-testid='sonicwall-protocol-hint']").text()

		expect(hint()).toBe(SONICWALL_PROTOCOL_HINTS.tls)

		options.value.protocol = "udp"
		await wrapper.setProps({ options: options.value })
		await nextTick()

		expect(hint()).toBe(SONICWALL_PROTOCOL_HINTS.udp)
	})
})
