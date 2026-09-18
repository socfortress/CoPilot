/**
 * OpenCTI surfaces (Threat Intel drawer section, alert IoC button) render only
 * for a verified connector. The availability answer is module-level state: an
 * alert page mounts one IoC card per IoC and they must share one request, while
 * a failure must not stick — the next caller has to be able to try again.
 */

import { beforeEach, describe, expect, it, vi } from "vitest"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { opencti: { getAvailability: (...args: unknown[]) => getAvailability(...args) } }
}))

async function load() {
	vi.resetModules()
	return (await import("../useOpenCTIAvailability")).useOpenCTIAvailability
}

function flush() {
	return new Promise(resolve => setTimeout(resolve, 0))
}

describe("useOpenCTIAvailability", () => {
	beforeEach(() => {
		getAvailability.mockReset()
	})

	it("shares one request between every caller on the page", async () => {
		getAvailability.mockResolvedValue({ data: { verified: true, platform_url: "http://opencti:8080" } })
		const useOpenCTIAvailability = await load()

		const first = useOpenCTIAvailability()
		const second = useOpenCTIAvailability()
		await flush()
		useOpenCTIAvailability()

		expect(getAvailability).toHaveBeenCalledTimes(1)
		expect(first.available.value).toBe(true)
		expect(second.available.value).toBe(true)
	})

	it("stays hidden for an unverified connector", async () => {
		getAvailability.mockResolvedValue({ data: { verified: false, platform_url: null } })
		const useOpenCTIAvailability = await load()

		const { available, objectUrl } = useOpenCTIAvailability()
		await flush()

		expect(available.value).toBe(false)
		expect(objectUrl("abc")).toBeNull()
	})

	it("does not cache a failure", async () => {
		getAvailability.mockRejectedValueOnce(new Error("network"))
		getAvailability.mockResolvedValueOnce({ data: { verified: true, platform_url: "http://opencti:8080" } })
		const useOpenCTIAvailability = await load()

		const { available } = useOpenCTIAvailability()
		await flush()
		expect(available.value).toBe(false)

		useOpenCTIAvailability()
		await flush()
		expect(getAvailability).toHaveBeenCalledTimes(2)
		expect(available.value).toBe(true)
	})

	it("builds OpenCTI's generic by-id link", async () => {
		getAvailability.mockResolvedValue({ data: { verified: true, platform_url: "http://opencti:8080" } })
		const useOpenCTIAvailability = await load()

		const { objectUrl } = useOpenCTIAvailability()
		await flush()

		expect(objectUrl("report--7ea432ac")).toBe("http://opencti:8080/dashboard/id/report--7ea432ac")
	})

	it("refresh() re-asks, so verifying the connector shows OpenCTI without a reload", async () => {
		getAvailability.mockResolvedValueOnce({ data: { verified: false, platform_url: null } })
		getAvailability.mockResolvedValueOnce({ data: { verified: true, platform_url: "http://opencti:8080" } })
		const useOpenCTIAvailability = await load()

		const { available, refresh } = useOpenCTIAvailability()
		await flush()
		expect(available.value).toBe(false)

		await refresh()
		expect(available.value).toBe(true)
	})
})
