import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export function getYearsSeries({ yearsCount = 8, name = "Trend" }) {
	const years = []

	for (let i = yearsCount - 1; i >= 0; i--) {
		years.push(dayjs().subtract(i, "y").format("YYYY"))
	}

	const categories = [...years]

	return {
		series: {
			name,
			data: years.map((v, i) => faker.number.int({ min: (i || 1) * 5, max: (i || 1) * 10 }))
		},
		categories
	}
}

export function getMonthsSeries({ name = "Trend" }) {
	const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	const categories = [...months]

	return {
		series: {
			name,
			data: months.map(() => faker.number.int({ min: 10, max: 93 }))
		},
		categories
	}
}

export function getWeekSeries({ name = "Trend" }) {
	const week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
	const categories = [...week]

	return {
		series: {
			name,
			data: week.map(() => faker.number.int({ min: 10, max: 93 }))
		},
		categories
	}
}

export function getAreaOpts({
	dark,
	colors,
	fontFamily,
	fontColor,
	categories,
	strokeWidth,
	customButtons,
	hideLegend,
	hideXaxisLabels
}: {
	dark?: boolean
	colors?: string[]
	fontFamily?: string
	fontColor?: string
	categories?: any[]
	customButtons?: any[]
	strokeWidth?: number
	hideLegend?: boolean
	hideXaxisLabels?: boolean
}) {
	const id = faker.string.nanoid()

	const overwriteCategories: any[] = categories ? [...categories] : []
	if (categories) {
		overwriteCategories[0] = ""
		overwriteCategories[categories.length - 1] = ""
	}

	return {
		chart: {
			id,
			stacked: false,
			offsetX: 0,
			offsetY: 0,
			toolbar: {
				show: customButtons?.length !== 0,
				tools: {
					download: false,
					selection: false,
					zoom: false,
					zoomin: false,
					zoomout: false,
					pan: false,
					reset: false,
					customIcons: customButtons || []
				}
			},
			dropShadow: {
				enabled: false
			},
			selection: {
				enabled: false
			}
		},
		stroke: {
			curve: "smooth",
			width: strokeWidth ?? 4
		},
		fill: {
			type: "gradient",
			gradient: {
				shadeIntensity: 0,
				opacityFrom: 0.4,
				opacityTo: 0,
				stops: [0, 100]
			}
		},
		grid: {
			show: false,
			yaxis: {
				lines: {
					show: false
				}
			},
			padding: {
				top: 0,
				right: -15,
				bottom: 18,
				left: 1
			}
		},
		dataLabels: {
			enabled: false,
			style: {
				fontFamily
			}
		},
		tooltip: {
			style: {
				fontFamily
			},
			theme: dark ? "dark" : "light"
		},
		legend: {
			position: "top",
			horizontalAlign: "right",
			show: !hideLegend
		},
		colors,
		xaxis: {
			categories,
			overwriteCategories,
			axisTicks: {
				show: false
			},
			axisBorder: {
				show: false
			},
			floating: true,
			position: "bottom",
			labels: {
				show: !hideXaxisLabels,
				offsetY: -2,
				style: {
					colors: fontColor,
					fontFamily,
					fontWeight: 500
				}
			},
			tickPlacement: "on",
			tooltip: {
				enabled: false
			}
		},
		yaxis: {
			show: false,

			title: {
				style: {
					fontFamily
				}
			},
			labels: {
				style: {
					fontFamily
				}
			}
		}
	}
}

export function getBarOpts({
	dark,
	colors,
	fontFamily,
	fontColor,
	categories,
	customButtons,
	hideLegend,
	hideXaxisLabels
}: {
	dark?: boolean
	colors?: string[]
	fontFamily?: string
	fontColor?: string
	categories?: any[]
	customButtons?: any[]
	strokeWidth?: number
	hideLegend?: boolean
	hideXaxisLabels?: boolean
}) {
	const id = faker.string.nanoid()

	const funcColor = function ({ dataPointIndex }: { dataPointIndex: number }) {
		if (colors) {
			if (colors[dataPointIndex]) {
				return colors[dataPointIndex]
			} else {
				return colors[0]
			}
		}
		return "grey"
	}

	return {
		chart: {
			id,
			stacked: false,
			toolbar: {
				show: customButtons?.length !== 0,
				tools: {
					download: false,
					selection: false,
					zoom: false,
					zoomin: false,
					zoomout: false,
					pan: false,
					reset: false,
					customIcons: customButtons || []
				}
			},
			dropShadow: {
				enabled: false
			},
			selection: {
				enabled: false
			}
		},
		plotOptions: {
			bar: {
				horizontal: false,
				columnWidth: "75%",
				borderRadius: 0,
				dataLabels: {
					position: "top" // top, center, bottom
				}
			}
		},
		grid: {
			show: false,
			yaxis: {
				lines: {
					show: false
				}
			},
			padding: {
				top: -10,
				right: 0,
				bottom: -16,
				left: 0
			}
		},
		dataLabels: {
			offsetY: -20,
			enabled: true,
			style: {
				colors: [funcColor],
				fontFamily
			}
		},
		tooltip: {
			theme: dark ? "dark" : "light",
			style: {
				fontFamily
			}
		},
		colors: [funcColor],
		legend: {
			position: "top",
			horizontalAlign: "right",
			show: !hideLegend,
			fontFamily
		},
		xaxis: {
			categories,
			axisTicks: {
				show: false
			},
			axisBorder: {
				show: false
			},
			floating: false,
			position: "bottom",
			labels: {
				show: !hideXaxisLabels,
				offsetY: -4,
				style: {
					colors: fontColor,
					fontFamily,
					fontWeight: 500
				}
			},
			tickPlacement: "top",
			tooltip: {
				enabled: false
			}
		},
		yaxis: {
			show: false,
			title: {
				style: {
					fontFamily
				}
			},
			labels: {
				style: {
					fontFamily
				}
			}
		}
	}
}
