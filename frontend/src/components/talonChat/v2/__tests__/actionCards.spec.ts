/**
 * The page's one poll for its approval cards (review of #1270): a hidden page reads nothing; N cards
 * cost one list read per tick, not N reads, and a card is read only when its row changed, when it
 * isn't listed (every minute), or to heal (every five); the tick backs off while nothing changes; a
 * proposal CoPilot has settled but talon-analyst hasn't is read every minute; a final one isn't;
 * logout stops it all.
 */
import type { TalonAction } from "@/types/talonActions"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
	cardsClock,
	knownAction,
	registerCard,
	resetTalonActions,
	TALON_CARDS_FAST_MS,
	TALON_CARDS_HEAL_MS,
	TALON_CARDS_MAX_MS,
	TALON_CARDS_SLOW_MS,
	unregisterCard
} from "../actionCards"
import { listOf, naiveUtc, response, talonAction } from "./fixtures"

const get = vi.fn()
const list = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonActions: {
			get: (...a: unknown[]) => get(...a),
			list: (...a: unknown[]) => list(...a)
		}
	}
}))

function setVisibility(state: "visible" | "hidden") {
	Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state })
	document.dispatchEvent(new Event("visibilitychange"))
}

const IDS = ["a1", "a2", "a3", "a4", "a5"]
let records: Record<string, TalonAction>

function serve() {
	get.mockImplementation(async (id: string) => response(records[id]))
	list.mockImplementation(async () => listOf(Object.values(records)))
}

async function settle() {
	await vi.advanceTimersByTimeAsync(0)
}

describe("the page's poll of its approval cards", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		resetTalonActions()
		get.mockReset()
		list.mockReset()
		setVisibility("visible")
		records = Object.fromEntries(IDS.map(id => [id, talonAction({ id })]))
		serve()
	})
	afterEach(() => {
		resetTalonActions()
		vi.useRealTimers()
	})

	it("five cards cost one list read a tick, and a read only for the row that changed", async () => {
		for (const id of IDS) registerCard(id)
		await settle()
		expect(get).toHaveBeenCalledTimes(5) // each card's first read
		await vi.advanceTimersByTimeAsync(TALON_CARDS_FAST_MS)
		expect(list).toHaveBeenCalledTimes(1)
		expect(list).toHaveBeenCalledWith("mine", expect.any(AbortSignal))
		expect(get).toHaveBeenCalledTimes(5)

		records.a3 = talonAction({ id: "a3", state: "denied", talon_status: "denied", can_decide: false })
		await vi.advanceTimersByTimeAsync(TALON_CARDS_MAX_MS)
		expect(get).toHaveBeenCalledTimes(6)
		expect(get).toHaveBeenLastCalledWith("a3", expect.any(AbortSignal))
		expect(knownAction("a3")?.action?.state).toBe("denied")

		// Ten minutes of nothing changing: list reads only (plus the heal), never N reads a tick.
		get.mockClear()
		list.mockClear()
		await vi.advanceTimersByTimeAsync(10 * 60_000)
		expect(list.mock.calls.length).toBeLessThanOrEqual((10 * 60_000) / TALON_CARDS_MAX_MS + 1)
		// The four still open cards each healed at most twice in ten minutes; the final one never.
		expect(get.mock.calls.filter(([id]) => id === "a3")).toHaveLength(0)
		expect(get.mock.calls.length).toBeLessThanOrEqual(4 * Math.ceil((10 * 60_000) / TALON_CARDS_HEAL_MS))
	})

	it("a decider's card (not their own proposal) reads the pending list too", async () => {
		records.a1 = talonAction({ id: "a1", is_requester: false })
		registerCard("a1")
		registerCard("a2")
		await settle()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_FAST_MS)
		expect(list.mock.calls.map(([scope]) => scope).sort()).toEqual(["mine", "pending"])
	})

	it("a hidden page reads nothing, and reads at once when shown again", async () => {
		registerCard("a1")
		await settle()
		setVisibility("hidden")
		get.mockClear()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_HEAL_MS * 2)
		expect(list).not.toHaveBeenCalled()
		expect(get).not.toHaveBeenCalled()
		setVisibility("visible")
		await settle()
		expect(list).toHaveBeenCalledTimes(1)
	})

	it("backs off while nothing changes: 10 s, 20 s, then every 30 s", async () => {
		registerCard("a1")
		await settle()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_FAST_MS)
		expect(list).toHaveBeenCalledTimes(1)
		await vi.advanceTimersByTimeAsync(2 * TALON_CARDS_FAST_MS - 1)
		expect(list).toHaveBeenCalledTimes(1)
		await vi.advanceTimersByTimeAsync(1)
		expect(list).toHaveBeenCalledTimes(2)
		await vi.advanceTimersByTimeAsync(TALON_CARDS_MAX_MS)
		expect(list).toHaveBeenCalledTimes(3)
		await vi.advanceTimersByTimeAsync(TALON_CARDS_MAX_MS)
		expect(list).toHaveBeenCalledTimes(4)
	})

	it("a proposal not in the list is read every minute", async () => {
		list.mockResolvedValue(listOf([]))
		registerCard("a1")
		await settle()
		get.mockClear()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_SLOW_MS - 1)
		expect(get).not.toHaveBeenCalled()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_MAX_MS)
		expect(get).toHaveBeenCalledTimes(1)
	})

	it.each([
		["refused", "pending"],
		["unreported", "approved"]
	])("settled here (%s) but not at talon-analyst: read every minute, so the thread heals", async (state, talon) => {
		records.a1 = talonAction({
			id: "a1",
			state,
			talon_status: talon,
			result_due_by: naiveUtc(20),
			can_decide: false
		})
		registerCard("a1")
		await settle()
		get.mockClear()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_SLOW_MS - 1)
		expect(get).not.toHaveBeenCalled()
		// talon-analyst expired it meanwhile; the next read shows it, and the poll stops.
		records.a1 = talonAction({ id: "a1", state, talon_status: "expired", can_decide: false })
		await vi.advanceTimersByTimeAsync(TALON_CARDS_MAX_MS)
		expect(get).toHaveBeenCalledTimes(1)
		expect(knownAction("a1")?.action?.talon_status).toBe("expired")
		list.mockClear()
		get.mockClear()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_HEAL_MS * 2)
		expect(list).not.toHaveBeenCalled()
		expect(get).not.toHaveBeenCalled()
	})

	it("an approved record past its result window is final, and the clock says so", async () => {
		records.a1 = talonAction({
			id: "a1",
			state: "unreported",
			talon_status: "approved",
			result_due_by: new Date(Date.now() + 45_000).toISOString().slice(0, 19),
			can_decide: false
		})
		registerCard("a1")
		await settle()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_SLOW_MS)
		expect(cardsClock.value).toBeGreaterThanOrEqual(Date.now() - TALON_CARDS_MAX_MS)
		list.mockClear()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_HEAL_MS)
		expect(list).not.toHaveBeenCalled()
	})

	it("a final record isn't polled; the last card gone, nothing is", async () => {
		records.a1 = talonAction({ id: "a1", state: "executed", talon_status: "executed" })
		registerCard("a1")
		registerCard("a2")
		await settle()
		unregisterCard("a2")
		await vi.advanceTimersByTimeAsync(TALON_CARDS_HEAL_MS * 2)
		expect(list).not.toHaveBeenCalled()
		expect(get).toHaveBeenCalledTimes(2)
	})

	it("logout stops the poll and forgets the records", async () => {
		registerCard("a1")
		await settle()
		resetTalonActions() // stores/auth.ts:setLogout
		expect(knownAction("a1")).toBeUndefined()
		await vi.advanceTimersByTimeAsync(TALON_CARDS_HEAL_MS * 2)
		expect(list).not.toHaveBeenCalled()
		expect(get).toHaveBeenCalledTimes(1)
	})
})
