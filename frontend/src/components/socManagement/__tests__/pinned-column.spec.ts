import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent, h, nextTick, useTemplateRef } from "vue"
import { usePinnedColumn } from "../composables/usePinnedColumn"

let resize: ((width: number) => void) | null = null

// jsdom has no layout: feed the box's width through a stub ResizeObserver.
class StubResizeObserver {
	constructor(private readonly callback: ResizeObserverCallback) {}
	observe(target: Element) {
		resize = width =>
			this.callback(
				[{ target, contentRect: { width, height: 10 }, contentBoxSize: [{ inlineSize: width, blockSize: 10 }] } as never],
				this as never
			)
	}

	unobserve() {}
	disconnect() {}
}

function mountWith(minWidth: number) {
	globalThis.ResizeObserver = StubResizeObserver as never
	let pinned!: ReturnType<typeof usePinnedColumn>
	mount(
		defineComponent({
			setup() {
				pinned = usePinnedColumn(useTemplateRef<HTMLElement>("box"), minWidth)
				return () => h("div", { ref: "box" })
			}
		})
	)
	return () => pinned.value
}

describe("usePinnedColumn", () => {
	it("pins while the box is unmeasured or at least as wide as the threshold, and not below it", async () => {
		const pinned = mountWith(500)
		await nextTick()
		expect(pinned()).toBe(true)
		resize?.(499)
		await nextTick()
		expect(pinned()).toBe(false)
		resize?.(500)
		await nextTick()
		expect(pinned()).toBe(true)
	})
})
