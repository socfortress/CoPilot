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

import type { Theme } from "@mui/material/styles"
import type { ReactNode } from "react"
import { createTheme, ThemeProvider } from "@mui/material/styles"
import { createElement } from "react"
import { useThemeStore } from "@/stores/theme"

let lightTheme: Theme | null = null
let darkTheme: Theme | null = null

function buildTheme(isDark: boolean): Theme {
	const themeStore = useThemeStore()

	return createTheme({
		palette: {
			mode: isDark ? "dark" : "light",
			...(isDark
				? {
						background: {
							default: "var(--bg-body-color) !important",
							paper: "var(--bg-default-color) !important"
						},
						primary: {
							main: themeStore.style["primary-color"]
						}
					}
				: {})
		},
		components: {
			MuiPaper: {
				styleOverrides: {
					root: {
						backgroundImage: "none !important",
						boxShadow: "none !important"
					}
				}
			},
			MuiCard: {
				styleOverrides: {
					root: {
						border: "1px solid var(--border-color) !important",
						borderColor: "var(--border-color) !important",
						backgroundImage: "none !important",
						backgroundColor: "var(--bg-secondary-color) !important"
					}
				}
			},
			MuiDrawer: {
				styleOverrides: {
					root: {
						zIndex: "2004 !important"
					},
					paper: {
						borderLeft: "none !important",
						borderTopLeftRadius: "var(--border-radius) !important",
						borderBottomLeftRadius: "var(--border-radius) !important"
					}
				}
			},
			MuiButton: {
				styleOverrides: {
					root: {
						borderRadius: "var(--border-radius) !important",
						boxShadow: "none !important"
					}
				}
			}
		},
		typography: {
			fontFamily: "var(--font-family)"
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
