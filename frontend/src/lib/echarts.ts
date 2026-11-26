/** Tree-shaken ECharts: only what Insights uses (loaded on demand, never in the main bundle). */
import { BarChart, LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import * as echarts from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer])

export default echarts
