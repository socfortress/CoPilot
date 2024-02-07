import { describe, it, expect } from "vitest"

import { mount } from "@vue/test-utils"
import TestScope from "../common/TestScope.vue"

describe("Sample Component", () => {
	it("renders properly", () => {
		const wrapper = mount(TestScope, { props: { msg: "Hello Vitest" } })
		expect(wrapper.text()).toContain("Hello Vitest")
	})
})
