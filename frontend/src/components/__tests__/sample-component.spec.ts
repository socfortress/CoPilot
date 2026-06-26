import { mount } from "@vue/test-utils"

import { describe, expect, it } from "vitest"
import TestScope from "../common/TestScope.vue"

describe("sample Component", () => {
	it("renders properly", () => {
		const wrapper = mount(TestScope, { props: { msg: "Hello Vitest" } })
		expect(wrapper.text()).toContain("Hello Vitest")
	})
})
