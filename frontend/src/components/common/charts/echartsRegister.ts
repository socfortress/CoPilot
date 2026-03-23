import { BarChart, LineChart, PieChart } from "echarts/charts"
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components"
import { use as echartsUse } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"

echartsUse([TooltipComponent, LegendComponent, GridComponent, PieChart, BarChart, LineChart, CanvasRenderer])
