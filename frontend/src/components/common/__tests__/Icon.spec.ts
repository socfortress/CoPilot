import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import Icon from "../Icon.vue"

/** Pending icon loads, resolved by hand to play them back in any order. */
const loads = vi.hoisted(() => new Map<string, (icon: unknown) => void>())

vi.mock("@iconify/vue", () => ({
	loadIcon: (name: string) => new Promise(resolve => loads.set(name, resolve)),
	Icon: defineComponent({
		props: { icon: { type: Object, required: true } },
		setup: props => () => h("svg", { "data-icon": (props.icon as { name: string }).name })
	})
}))

function resolve(name: string) {
	loads.get(name)?.({ name, body: "", width: 24, height: 24 })
}

function shown(wrapper: ReturnType<typeof mount>) {
	return wrapper.find("[data-icon]").attributes("data-icon") ?? null
}

beforeEach(() => loads.clear())

describe("icon", () => {
	it("shows the icon it was asked for", async () => {
		const wrapper = mount(Icon, { props: { name: "uil:edit-alt" } })
		resolve("uil:edit-alt")
		await flushPromises()
		expect(shown(wrapper)).toBe("uil:edit-alt")
	})

	it("never lets a slower, superseded load replace the current icon (#1217)", async () => {
		const wrapper = mount(Icon, { props: { name: "uil:edit-alt" } })
		resolve("uil:edit-alt")
		await flushPromises()

		// Saving: the spinner is asked for, then the save ends and the edit icon is asked for again.
		await wrapper.setProps({ name: "eos-icons:loading" })
		await wrapper.setProps({ name: "uil:edit-alt" })
		resolve("uil:edit-alt")
		await flushPromises()
		// The spinner's first download lands last.
		resolve("eos-icons:loading")
		await flushPromises()

		expect(shown(wrapper)).toBe("uil:edit-alt")
	})

	it("shows nothing once the name is cleared", async () => {
		const wrapper = mount(Icon, { props: { name: "carbon:pin-filled" } })
		resolve("carbon:pin-filled")
		await flushPromises()
		await wrapper.setProps({ name: undefined })
		await flushPromises()
		expect(wrapper.find("[data-icon]").exists()).toBe(false)
	})
})
