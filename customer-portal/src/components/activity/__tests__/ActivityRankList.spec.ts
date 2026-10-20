import type { ActivityCount } from "@/types/activity"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { defineComponent, h } from "vue"
import ActivityRankList from "../ActivityRankList.vue"

const RouterLinkStub = defineComponent({
	props: { to: { type: Object, required: true } },
	setup:
		(props, { slots }) =>
		() =>
			h("a", { "data-to": JSON.stringify(props.to) }, slots.default?.())
})

const ITEMS: ActivityCount[] = [
	{ key: "wazuh", label: null, count: 50, previous: 20 },
	{ key: "‮evil", label: null, count: 1, previous: 0 }
]

function render(link?: (item: ActivityCount, period: "current" | "previous") => object | null) {
	return mount(ActivityRankList, {
		props: { items: ITEMS, testid: "list", link: link as never },
		global: { stubs: { RouterLink: RouterLinkStub } }
	})
}

beforeEach(() => setActivePinia(createPinia()))

/** One breakdown as a ranked list of bars (#1284). */
describe("activityRankList", () => {
	it("draws this period as the bar and the period before as a tick on the same scale", () => {
		const wrapper = render()
		const [first, second] = wrapper.findAll("[data-testid=list-row]")
		const bar = first!.find("[role=presentation] > div")
		expect(bar.attributes("style")).toContain("width: 100%")
		const tick = first!.find("[title='The period before: 20']")
		expect(tick.attributes("style")).toContain("left: calc(40% - 1px)")
		// Nothing before: no tick, and the change reads "new".
		expect(second!.find("[title^='The period before']").exists()).toBe(false)
		expect(second!.get("[data-testid=activity-row-delta]").text()).toBe("new")
		expect(first!.get("[data-testid=activity-row-delta]").text()).toBe("+30")
	})

	it("isolates a label's direction, whatever characters it carries", () => {
		const label = render().findAll("[data-testid=activity-row-label]")[1]!
		expect(label.find("bdi").text()).toBe("‮evil")
	})

	it("links each period's count where the caller says, and nothing without a link", () => {
		const linked = render((item, period) => ({ name: "AlertsList", query: { source: item.key, period } }))
		const row = linked.findAll("[data-testid=list-row]")[0]!
		expect(JSON.parse(row.get("[data-testid=activity-row-count]").attributes("data-to")!).query).toEqual({
			source: "wazuh",
			period: "current"
		})
		expect(JSON.parse(row.get("[data-testid=activity-row-previous]").attributes("data-to")!).query.period).toBe(
			"previous"
		)
		// A previous count of 0 lists nothing: not a link.
		expect(
			linked.findAll("[data-testid=list-row]")[1]!.get("[data-testid=activity-row-previous]").element.tagName
		).toBe("SPAN")

		const plain = render()
		expect(plain.find("a").exists()).toBe(false)
	})
})
