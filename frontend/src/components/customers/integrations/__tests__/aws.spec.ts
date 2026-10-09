import { mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import AwsDeployResult from "../AwsDeployResult.vue"
import {
	authKeyPlaceholder,
	isMultiInstanceIntegration,
	isOptionalAuthKey,
	isWriteOnlyAuthKey,
	REDACTED_AUTH_VALUE
} from "../utils"

// CodeSource highlights through a directive; the plain text is all these tests look at.
vi.mock("@/components/common/CodeSource.vue", () => ({
	default: { props: ["code"], template: "<pre data-testid='code'>{{ code }}</pre>" }
}))

describe("the AWS integration helpers", () => {
	it("allows several AWS accounts per customer", () => {
		expect(isMultiInstanceIntegration("AWS")).toBe(true)
		expect(isMultiInstanceIntegration("Mimecast")).toBe(false)
	})

	it("lets only the documented AWS keys stay empty", () => {
		for (const key of ["AWS_ACCOUNT_ALIAS", "AWS_ORGANIZATION_ID", "ONLY_LOGS_AFTER"]) {
			expect(isOptionalAuthKey("AWS", key)).toBe(true)
		}
		for (const key of ["ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "AWS_ACCOUNT_ID", "BUCKET_NAME", "SERVICES"]) {
			expect(isOptionalAuthKey("AWS", key)).toBe(false)
		}
		// Other integrations keep every key required.
		expect(isOptionalAuthKey("Office365", "API_TYPE")).toBe(false)
	})

	it("treats only the AWS secret as write-only", () => {
		expect(isWriteOnlyAuthKey("SECRET_ACCESS_KEY")).toBe(true)
		expect(isWriteOnlyAuthKey("CLIENT_SECRET")).toBe(false)
		expect(REDACTED_AUTH_VALUE).toBe("********")
	})

	it("explains the SERVICES format", () => {
		expect(authKeyPlaceholder("AWS", "SERVICES")).toContain("guardduty:guardduty")
		expect(authKeyPlaceholder("Mimecast", "APP_ID")).toBe("Input APP_ID...")
	})
})

describe("the AWS deploy result dialog", () => {
	const awsConfig = {
		detected: false,
		file_path: "/root/.aws/config",
		summary: "CoPilot cannot read or write /root/.aws/config",
		steps: ["Log in to the Wazuh master node.", "sudo systemctl restart wazuh-manager"],
		contents: "[default]\nregion = eu-west-1\n"
	}

	it("shows the steps and the section to add", () => {
		const wrapper = mount(AwsDeployResult, { props: { message: "Deployed.", awsConfig } })

		expect(wrapper.text()).toContain("CoPilot cannot read or write /root/.aws/config")
		expect(wrapper.findAll("li")).toHaveLength(2)
		expect(wrapper.get("[data-testid='code']").text()).toContain("[default]")
	})

	it("shows every warning", () => {
		const wrapper = mount(AwsDeployResult, {
			props: { message: "Deployed.", warnings: ["validation skipped", "wodle disabled"], awsConfig: null }
		})

		expect(wrapper.text()).toContain("validation skipped")
		expect(wrapper.text()).toContain("wodle disabled")
	})
})
