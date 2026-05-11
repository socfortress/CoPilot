// Shared Material UI theme bridge for the React-mounted Shuffle embeds.
//
// Background: `@shuffleio/shuffle-mcps` is built with `@mui/material`.
// Without a `<ThemeProvider>` wrapping the React mount, MUI falls back
// to its built-in light-mode palette — which, against CoPilot's dark
// backdrop, looks washed-out and transparent (the AppDetailDrawer in
// particular ended up unreadable for users on the default theme).
//
// We expose:
//   - `getMuiTheme(isDark)` — returns a memoised MUI Theme matching
//     CoPilot's light/dark mode. We don't pipe every Naive UI token in
//     (the surface area is huge and the MUI palette has its own
//     semantics) — just the mode plus a darkened paper background so
//     drawer/menu surfaces are opaque against the page underneath.
//   - `MuiProvider` — small React component that wraps children in
//     `<ThemeProvider value={mui-theme}>`. Each embed wrapper renders
//     this around the package's exported component.
import type { ReactNode } from "react"
import type { Theme } from "@mui/material/styles"
import { createTheme, ThemeProvider } from "@mui/material/styles"
import { createElement } from "react"

let lightTheme: Theme | null = null
let darkTheme: Theme | null = null

function buildTheme(isDark: boolean): Theme {
	return createTheme({
		palette: {
			mode: isDark ? "dark" : "light",
			// MUI's default dark mode uses #121212 / #1e1e1e — slightly too
			// flat against CoPilot's elevated panels. Bump it a touch so
			// drawer/menu surfaces sit visibly above the page.
			...(isDark
				? {
						background: { default: "#171819", paper: "#1e2024" }
					}
				: {})
		},
		// Inherit CoPilot's font stack so the embeds don't introduce a
		// second typeface inside the same view.
		typography: {
			fontFamily:
				'"Public Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
		}
	})
}

export function getMuiTheme(isDark: boolean): Theme {
	if (isDark) {
		if (!darkTheme) darkTheme = buildTheme(true)
		return darkTheme
	}
	if (!lightTheme) lightTheme = buildTheme(false)
	return lightTheme
}

export function MuiProvider(props: { isDark: boolean; children: ReactNode }) {
	return createElement(ThemeProvider as never, { theme: getMuiTheme(props.isDark) }, props.children)
}
