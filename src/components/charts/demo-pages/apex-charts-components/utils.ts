/*
    // this function will generate output in this format
    // data = [
        [timestamp, 23],
        [timestamp, 33],
        [timestamp, 12]
        ...
    ]
  */
export function generateDayWiseTimeSeries(
	baseval: number,
	count: number,
	yrange: {
		min: number
		max: number
	}
) {
	let i = 0
	const series = []
	while (i < count) {
		const x = baseval
		const y = Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min

		series.push([x, y])
		baseval += 86400000
		i++
	}
	return series
}
