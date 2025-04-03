export default {
	theme: {
		fontFamily: {
			sans: ["var(--font-family)", "sans-serif"],
			serif: ["var(--font-family-display)", "serif"],
			display: ["var(--font-family-display)", "serif"],
			mono: ["var(--font-family-mono)", "monospace"]
		},
		extend: {
			colors: {
				primary: "rgb(var(--primary-color-rgb))",
				success: "rgb(var(--success-color-rgb))",
				error: "rgb(var(--error-color-rgb))",
				warning: "rgb(var(--warning-color-rgb))",
				info: "rgb(var(--info-color-rgb))",
				border: "rgb(var(--border-color-rgb))",
				hover: "rgb(var(--hover-color-rgb))",
				extra: {
					1: "rgb(var(--extra1-color-rgb))",
					2: "rgb(var(--extra2-color-rgb))",
					3: "rgb(var(--extra3-color-rgb))",
					4: "rgb(var(--extra4-color-rgb))"
				}
			},
			backgroundColor: {
				default: "rgb(var(--bg-default-color-rgb))",
				secondary: "rgb(var(--bg-secondary-color-rgb))",
				body: "rgb(var(--bg-body-color-rgb))",
				sidebar: "rgb(var(--bg-sidebar-color-rgb))"
			},
			textColor: {
				default: "rgb(var(--fg-default-color-rgb))",
				secondary: "rgb(var(--fg-secondary-color-rgb))",
				tertiary: "rgb(var(--fg-tertiary-color-rgb))"
			},
			animation: {
				fade: "fade 0.3s forwards"
			},
			keyframes: {
				fade: {
					from: { opacity: 0 },
					to: { opacity: 1 }
				}
			},
			screens: {
				xs: "460px"
			},
			spacing: {
				"50vh": "50vh",
				"90vw": "90vw",
				"60vh": "60vh",
				"20vh": "20vh",
				"50vw": "50vw"
			}
		}
	}
}
