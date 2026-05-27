/** Palette condivisa per grafici dashboard (segmenti pie, barre distribuite, …). */
export const CHART_COLORS = [
	"#8a3ffc",
	"#33b1ff",
	"#007d79",
	"#ff7eb6",
	"#fa4d56",
	"#fff1f1",
	"#6fdc8c",
	"#4589ff",
	"#d12771",
	"#d2a106",
	"#08bdba",
	"#bae6ff",
	"#ba4e00",
	"#d4bbff"
] as const

/** ECharts 6: equivalente a `grid.containLabel: true` senza il plugin legacy. */
export const CHART_GRID_CONTAIN_AXIS_LABELS = {
	outerBoundsMode: "same",
	outerBoundsContain: "axisLabel"
} as const
