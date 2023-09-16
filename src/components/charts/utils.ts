import { colord, random } from "colord"
import _max from "lodash/max"

interface ChartColors {
	color?: string
	type?: "random"
	highlight?: boolean[]
}

export function getChartColors({ color, type, highlight }: ChartColors): string[] {
	if (type === "random") {
		return new Array(15).fill(null).map(() => random().desaturate(0.55).lighten(0.15).toRgbString())
	}

	if (color && highlight && highlight.length) {
		return highlight.map(v => (v ? colord(color).toRgbString() : colord(color).alpha(0.3).toRgbString()))
	}

	if (color) {
		return [colord(color).toRgbString()]
	}

	return ["grey"]
}

export function getHighlightMap(series: number[]): boolean[] {
	const max = _max(series)
	return series.map(v => v === max)
}
