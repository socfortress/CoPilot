/**
 * Dev-only element picker.
 *
 * Purpose: make "change THIS bit of the UI" unambiguous. Point at any element on
 * the page and it reports the component file that owns it, its classes and its
 * computed box/type metrics, so a visual request can be acted on without anyone
 * having to describe the element in prose.
 *
 * It resolves the owning component through `__vueParentComponent.type.__file`,
 * which only exists in a development build — in a production build every pick
 * would report an unknown file. That is why this module is imported behind
 * `import.meta.env.DEV` and never reaches the shipped bundle.
 *
 * Everything (picks, highlights, toolbar position, whether the mode was on)
 * survives a reload through sessionStorage, so a picking session is not lost the
 * moment a file is saved and Vite reloads the page.
 */

interface Pick {
	n: number
	/** CSS path from <body>, so a highlight can be re-attached after a reload. */
	path: string
	file: string
	tag: string
	classes: string
	text: string
	size: string
	style: Record<string, string>
}

const PICKS_KEY = "dev.picker.picks"
const ACTIVE_KEY = "dev.picker.active"
const HUD_KEY = "dev.picker.hud"
const HOTKEY = "KeyP" // with ctrl+alt — rarely bound by the browser or the OS

/** Marks the picker's own chrome so it never picks itself. */
const UI_ATTR = "data-picker-ui"

const ACCENT = "#ffb600"
const PICKED = "#18a058"

let picks: Pick[] = []
let teardown: (() => void) | null = null
let hudCount: HTMLElement | null = null
let markerLayer: HTMLDivElement | null = null
let markerTimer: ReturnType<typeof setInterval> | null = null

// --- session state ----------------------------------------------------------

function readSession<T>(key: string, fallback: T): T {
	try {
		const raw = sessionStorage.getItem(key)
		return raw ? (JSON.parse(raw) as T) : fallback
	} catch {
		return fallback
	}
}

function writeSession(key: string, value: unknown) {
	try {
		sessionStorage.setItem(key, JSON.stringify(value))
	} catch {
		/* private mode, quota — the picker still works, it just won't survive a reload */
	}
}

// --- element identity -------------------------------------------------------

/** Walk up the DOM until a node carries a Vue instance that knows its source file. */
function fileOf(node: Element | null): string {
	let current: (Element & { __vueParentComponent?: { type?: { __file?: string } } }) | null = node
	let hops = 0
	while (current && hops < 40) {
		const file = current.__vueParentComponent?.type?.__file
		if (file) return file.split("/frontend/src/").pop() || file
		current = current.parentElement
		hops++
	}
	return "?"
}

/**
 * A structural path (nth-of-type chain) rather than an id or class selector:
 * most nodes here have neither, and Tailwind class strings are not unique.
 */
function domPath(el: Element): string {
	const parts: string[] = []
	let node: Element | null = el
	while (node && node !== document.body && parts.length < 20) {
		const current: Element = node
		const parent: Element | null = current.parentElement
		if (!parent) break
		const tag = current.tagName.toLowerCase()
		const sameTag = Array.from(parent.children).filter(c => c.tagName === current.tagName)
		parts.unshift(sameTag.length > 1 ? `${tag}:nth-of-type(${sameTag.indexOf(current) + 1})` : tag)
		node = parent
	}
	return `body > ${parts.join(" > ")}`
}

function resolveEl(pick: Pick): Element | null {
	try {
		return document.querySelector(pick.path)
	} catch {
		return null
	}
}

/** True for the picker's own toolbar/overlays, which must never be pickable. */
function isPickerUi(target: EventTarget | null): boolean {
	return !!(target as Element | null)?.closest?.(`[${UI_ATTR}]`)
}

// --- highlights of picked elements ------------------------------------------
// Deliberately outlive pick mode: after Esc you still want to see what you chose.

function ensureMarkerLayer(): HTMLDivElement {
	if (markerLayer?.isConnected) return markerLayer
	markerLayer = document.createElement("div")
	markerLayer.setAttribute(UI_ATTR, "")
	Object.assign(markerLayer.style, {
		position: "fixed",
		inset: "0",
		zIndex: "2147483646",
		pointerEvents: "none"
	})
	document.body.appendChild(markerLayer)
	window.addEventListener("scroll", positionMarkers, true)
	window.addEventListener("resize", positionMarkers)
	// Layout moves for reasons no event reports (async data, HMR patches), so a
	// slow tick keeps the boxes glued without a per-frame loop.
	markerTimer = setInterval(positionMarkers, 400)
	return markerLayer
}

function renderMarkers() {
	if (!picks.length) {
		markerLayer?.replaceChildren()
		return
	}
	const layer = ensureMarkerLayer()
	layer.replaceChildren()
	for (const pick of picks) {
		const marker = document.createElement("div")
		marker.dataset.pick = String(pick.n)
		Object.assign(marker.style, {
			position: "fixed",
			border: `2px solid ${PICKED}`,
			background: "rgba(24,160,88,.10)",
			borderRadius: "4px",
			display: "none"
		})
		const badge = document.createElement("div")
		badge.textContent = String(pick.n)
		Object.assign(badge.style, {
			position: "absolute",
			top: "-9px",
			left: "-9px",
			minWidth: "18px",
			height: "18px",
			borderRadius: "9px",
			background: PICKED,
			color: "#fff",
			font: "bold 11px/18px monospace",
			textAlign: "center",
			padding: "0 4px"
		})
		marker.appendChild(badge)
		layer.appendChild(marker)
	}
	positionMarkers()
}

function positionMarkers() {
	if (!markerLayer?.isConnected) return
	for (const marker of Array.from(markerLayer.children) as HTMLElement[]) {
		const pick = picks.find(p => String(p.n) === marker.dataset.pick)
		const el = pick ? resolveEl(pick) : null
		if (!el) {
			marker.style.display = "none"
			continue
		}
		const r = el.getBoundingClientRect()
		Object.assign(marker.style, {
			display: r.width || r.height ? "block" : "none",
			left: `${r.left}px`,
			top: `${r.top}px`,
			width: `${r.width}px`,
			height: `${r.height}px`
		})
	}
}

function clearMarkers() {
	markerLayer?.remove()
	markerLayer = null
	if (markerTimer) {
		clearInterval(markerTimer)
		markerTimer = null
	}
	window.removeEventListener("scroll", positionMarkers, true)
	window.removeEventListener("resize", positionMarkers)
}

// --- toolbar ----------------------------------------------------------------

function hudButton(label: string, title: string, onClick: () => void): HTMLButtonElement {
	const b = document.createElement("button")
	b.type = "button"
	b.textContent = label
	b.title = title
	Object.assign(b.style, {
		font: "11px/1 monospace",
		color: "#fff",
		background: "transparent",
		border: `1px solid ${ACCENT}`,
		borderRadius: "4px",
		padding: "4px 7px",
		cursor: "pointer"
	})
	b.addEventListener("click", e => {
		e.preventDefault()
		e.stopPropagation()
		onClick()
	})
	// The toolbar itself is draggable; a press on a button must not start a drag.
	b.addEventListener("pointerdown", e => e.stopPropagation())
	return b
}

function buildHud(): HTMLElement {
	const hud = document.createElement("div")
	hud.setAttribute(UI_ATTR, "")
	const saved = readSession<{ left: number; top: number } | null>(HUD_KEY, null)
	Object.assign(hud.style, {
		position: "fixed",
		left: saved ? `${saved.left}px` : "12px",
		top: saved ? `${saved.top}px` : `${window.innerHeight - 46}px`,
		zIndex: "2147483647",
		display: "flex",
		alignItems: "center",
		gap: "8px",
		background: "#111",
		color: "#fff",
		font: "12px/1.4 monospace",
		padding: "6px 10px",
		borderRadius: "6px",
		border: `1px solid ${ACCENT}`,
		cursor: "move",
		userSelect: "none"
	})

	const grip = document.createElement("span")
	grip.textContent = "⠿"
	grip.style.color = ACCENT
	grip.title = "Drag to move"

	hudCount = document.createElement("span")

	hud.append(grip, hudCount, hudButton("reset", "Clear every pick", clear), hudButton("✕", "Exit pick mode", stop))

	// Drag with pointer events (works with trackpad or pen) and pointer capture,
	// so a fast drag that outruns the cursor does not drop the toolbar.
	let dx = 0
	let dy = 0
	hud.addEventListener("pointerdown", e => {
		const r = hud.getBoundingClientRect()
		dx = e.clientX - r.left
		dy = e.clientY - r.top
		hud.setPointerCapture(e.pointerId)
		const onMove = (ev: PointerEvent) => {
			// Clamped, so the toolbar can never be dragged out of reach.
			const left = Math.min(Math.max(0, ev.clientX - dx), window.innerWidth - hud.offsetWidth)
			const top = Math.min(Math.max(0, ev.clientY - dy), window.innerHeight - hud.offsetHeight)
			hud.style.left = `${left}px`
			hud.style.top = `${top}px`
		}
		const onUp = () => {
			hud.removeEventListener("pointermove", onMove)
			hud.removeEventListener("pointerup", onUp)
			writeSession(HUD_KEY, { left: parseInt(hud.style.left, 10), top: parseInt(hud.style.top, 10) })
		}
		hud.addEventListener("pointermove", onMove)
		hud.addEventListener("pointerup", onUp)
	})

	return hud
}

function refreshHud() {
	if (hudCount) hudCount.textContent = `PICK MODE · ${picks.length} picked`
}

// --- mode -------------------------------------------------------------------

function start() {
	if (teardown) return
	writeSession(ACTIVE_KEY, true)

	const box = document.createElement("div")
	box.setAttribute(UI_ATTR, "")
	Object.assign(box.style, {
		position: "fixed",
		zIndex: "2147483645",
		pointerEvents: "none",
		border: `2px solid ${ACCENT}`,
		background: "rgba(255,182,0,.12)",
		borderRadius: "4px",
		display: "none"
	})

	const tip = document.createElement("div")
	tip.setAttribute(UI_ATTR, "")
	Object.assign(tip.style, {
		position: "fixed",
		zIndex: "2147483645",
		pointerEvents: "none",
		display: "none",
		background: "#111",
		color: ACCENT,
		font: "12px/1.4 monospace",
		padding: "3px 6px",
		borderRadius: "4px",
		maxWidth: "60vw",
		whiteSpace: "nowrap",
		overflow: "hidden",
		textOverflow: "ellipsis"
	})

	const hud = buildHud()
	refreshHud()
	document.body.append(box, tip, hud)

	const onMove = (e: MouseEvent) => {
		const el = e.target as Element | null
		if (!el?.getBoundingClientRect || isPickerUi(el)) {
			box.style.display = "none"
			tip.style.display = "none"
			return
		}
		const r = el.getBoundingClientRect()
		Object.assign(box.style, {
			display: "block",
			left: `${r.left}px`,
			top: `${r.top}px`,
			width: `${r.width}px`,
			height: `${r.height}px`
		})
		Object.assign(tip.style, { display: "block", left: `${r.left}px`, top: `${Math.max(0, r.top - 22)}px` })
		tip.textContent = `${fileOf(el)}  ·  ${el.tagName.toLowerCase()}`
	}

	// Capture phase + preventDefault: while picking, a click selects an element
	// instead of activating whatever is under the cursor. The toolbar is exempt,
	// otherwise its own buttons would be picked rather than pressed.
	const onClick = (e: MouseEvent) => {
		if (isPickerUi(e.target)) return
		e.preventDefault()
		e.stopPropagation()

		const el = e.target as Element
		const path = domPath(el)

		// Clicking a picked element again unpicks it: with the selection visible on
		// the page, "click to toggle" is the behaviour the highlight implies.
		const existing = picks.findIndex(p => p.path === path)
		if (existing !== -1) {
			const [removed] = picks.splice(existing, 1)
			picks.forEach((p, i) => (p.n = i + 1))
			writeSession(PICKS_KEY, picks)
			renderMarkers()
			refreshHud()
			// eslint-disable-next-line no-console
			console.log(`[PICK] removed #${removed.n} (${removed.file})`)
			return
		}

		const cs = getComputedStyle(el)
		const r = el.getBoundingClientRect()
		const pick: Pick = {
			n: picks.length + 1,
			path,
			file: fileOf(el),
			tag: el.tagName.toLowerCase(),
			classes: el.className?.toString().slice(0, 160) || "",
			text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 70),
			size: `${Math.round(r.width)}x${Math.round(r.height)}`,
			style: {
				font: `${cs.fontSize}/${cs.lineHeight}`,
				weight: cs.fontWeight,
				color: cs.color,
				pad: cs.padding,
				margin: cs.margin,
				gap: cs.gap,
				radius: cs.borderRadius,
				bg: cs.backgroundColor
			}
		}
		picks.push(pick)
		writeSession(PICKS_KEY, picks)
		renderMarkers()
		refreshHud()
		// eslint-disable-next-line no-console
		console.log(`[PICK] ${JSON.stringify(pick)}`)
	}

	const onKey = (e: KeyboardEvent) => {
		if (e.key === "Escape") stop()
	}

	document.addEventListener("mousemove", onMove, true)
	document.addEventListener("click", onClick, true)
	document.addEventListener("keydown", onKey, true)

	teardown = () => {
		document.removeEventListener("mousemove", onMove, true)
		document.removeEventListener("click", onClick, true)
		document.removeEventListener("keydown", onKey, true)
		box.remove()
		tip.remove()
		hud.remove()
		hudCount = null
	}

	// eslint-disable-next-line no-console
	console.log(`[PICK] mode on — ${picks.length} pick(s) carried over`)
}

function stop() {
	teardown?.()
	teardown = null
	writeSession(ACTIVE_KEY, false)
	// eslint-disable-next-line no-console
	console.log("[PICK] mode off")
}

function clear() {
	picks = []
	writeSession(PICKS_KEY, picks)
	clearMarkers()
	refreshHud()
	// eslint-disable-next-line no-console
	console.log("[PICK] cleared")
}

function list() {
	return picks
}

export function installElementPicker() {
	picks = readSession<Pick[]>(PICKS_KEY, [])

	Object.defineProperty(window, "__picker", {
		value: {
			start,
			stop,
			clear,
			list,
			get picks() {
				return picks
			}
		},
		configurable: true
	})

	// Ctrl+Alt+P toggles it without needing the console at all.
	window.addEventListener("keydown", e => {
		if (e.ctrlKey && e.altKey && e.code === HOTKEY) {
			e.preventDefault()
			if (teardown) stop()
			else start()
		}
	})

	// Restored picks get their highlights back even if pick mode itself was off:
	// the selection is page state, not a mode.
	if (picks.length) renderMarkers()

	// A picking session that was open when the page reloaded resumes itself —
	// saving a file must not silently drop the mode you were working in.
	if (readSession(ACTIVE_KEY, false)) start()

	// eslint-disable-next-line no-console
	console.info(
		"%c🎯 Element picker ready%c\n" +
			"Type USE_PICKER_MODE in Claude Code to start it, or press Ctrl+Alt+P.\n" +
			"Then click the elements you want changed — the toolbar has reset and exit, and drags anywhere.",
		`color:${ACCENT};font-weight:bold`,
		"color:inherit"
	)
}
