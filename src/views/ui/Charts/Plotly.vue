<template>
    <div class="page-plotly scrollable">
        <div class="page-header">
            <h1>Plotly</h1>
            <h4>
                <a href="https://plot.ly/javascript/" target="_blank"><i class="mdi mdi-link-variant"></i>reference</a>
            </h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Plotly</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Stacked Area Chart</h2>
            <div class="chart-box">
                <div ref="stackedArea"></div>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Colored and Styled Bar Chart</h2>
            <div class="chart-box">
                <div ref="bar"></div>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Sankey Diagram</h2>
            <div class="chart-box">
                <div ref="sankey"></div>
            </div>
        </div>

        <!--<div class="card-base card-shadow--medium p-20 mt-30">
			<h2 class="mt-0">Lines on an Orthographic Map</h2>
			<div class="chart-box">
				<div ref="map"></div>
			</div>
		</div>-->

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Fully Styled Box Plot</h2>
            <div class="chart-box">
                <div ref="boxPlot"></div>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Time Series with Rangeslider</h2>
            <div class="chart-box">
                <div ref="time"></div>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-20 mt-30">
            <h2 class="mt-0">Wind Rose Chart</h2>
            <div class="chart-box">
                <div ref="polar"></div>
            </div>
        </div>
    </div>
</template>

<script>
import Plotly from "plotly.js/lib/core"
import PlotlyBar from "plotly.js/lib/bar"
import PlotlyBox from "plotly.js/lib/box"
import PlotlySankey from "plotly.js/lib/sankey"

/*import PlotlyScatter3d from 'plotly.js/lib/scatter3d'
import PlotlySurface from 'plotly.js/lib/surface'
import PlotlyMesh3d from 'plotly.js/lib/mesh3d'*/

Plotly.register(PlotlyBar)
Plotly.register(PlotlyBox)
Plotly.register(PlotlySankey)

/*Plotly.register(PlotlyScatter3d)
Plotly.register(PlotlySurface)
Plotly.register(PlotlyMesh3d)*/

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "PlotlyPage",
    data() {
        return {
            rows: []
        }
    },
    mounted() {
        /*  Stacked Area Chart  */
        var traces = [
            { x: [1, 2, 3], y: [2, 1, 4], fill: "tozeroy" },
            { x: [1, 2, 3], y: [1, 1, 2], fill: "tonexty" },
            { x: [1, 2, 3], y: [3, 0, 2], fill: "tonexty" }
        ]
        function stackedArea(traces) {
            for (var i = 1; i < traces.length; i++) {
                for (var j = 0; j < Math.min(traces[i]["y"].length, traces[i - 1]["y"].length); j++) {
                    traces[i]["y"][j] += traces[i - 1]["y"][j]
                }
            }
            return traces
        }
        Plotly.newPlot(this.$refs.stackedArea, stackedArea(traces), { title: "stacked and filled line chart" })

        /*  Colored and Styled Bar Chart  */
        ;(() => {
            var trace1 = {
                x: [
                    1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
                    2011, 2012
                ],
                y: [219, 146, 112, 127, 124, 180, 236, 207, 236, 263, 350, 430, 474, 526, 488, 537, 500, 439],
                name: "Rest of world",
                marker: { color: "rgb(55, 83, 109)" },
                type: "bar"
            }
            var trace2 = {
                x: [
                    1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
                    2011, 2012
                ],
                y: [16, 13, 10, 11, 28, 37, 43, 55, 56, 88, 105, 156, 270, 299, 340, 403, 549, 499],
                name: "China",
                marker: { color: "rgb(26, 118, 255)" },
                type: "bar"
            }
            var data = [trace1, trace2]
            var layout = {
                title: "US Export of Plastic Scrap",
                xaxis: {
                    tickfont: {
                        size: 14,
                        color: "rgb(107, 107, 107)"
                    }
                },
                yaxis: {
                    title: "USD (millions)",
                    titlefont: {
                        size: 16,
                        color: "rgb(107, 107, 107)"
                    },
                    tickfont: {
                        size: 14,
                        color: "rgb(107, 107, 107)"
                    }
                },
                legend: {
                    x: 0,
                    y: 1.0,
                    bgcolor: "rgba(255, 255, 255, 0)",
                    bordercolor: "rgba(255, 255, 255, 0)"
                },
                barmode: "group",
                bargap: 0.15,
                bargroupgap: 0.1
            }
            Plotly.newPlot(this.$refs.bar, data, layout)
        })()

        /*  Sankey Diagram  */
        Plotly.d3.json(
            "https://raw.githubusercontent.com/plotly/plotly.js/master/test/image/mocks/sankey_energy.json",
            fig => {
                var data = {
                    type: "sankey",
                    domain: {
                        x: [0, 1],
                        y: [0, 1]
                    },
                    orientation: "h",
                    valueformat: ".0f",
                    valuesuffix: "TWh",
                    node: {
                        pad: 15,
                        thickness: 15,
                        line: {
                            color: "black",
                            width: 0.5
                        },
                        label: fig.data[0].node.label,
                        color: fig.data[0].node.color
                    },
                    link: {
                        source: fig.data[0].link.source,
                        target: fig.data[0].link.target,
                        value: fig.data[0].link.value,
                        label: fig.data[0].link.label
                    }
                }
                var data = [data]
                var layout = {
                    title: "Energy forecast for 2050<br>Source: Department of Energy & Climate Change, Tom Counsell via <a href='https://bost.ocks.org/mike/sankey/'>Mike Bostock</a>",
                    //width: 1118,
                    height: 772,
                    font: {
                        size: 10
                    }
                }
                Plotly.plot(this.$refs.sankey, data, layout)
            }
        )

        /*  Lines on an Orthographic Map
		Plotly.d3.csv('https://raw.githubusercontent.com/plotly/datasets/master/globe_contours.csv',(err, rows) => {
			function unpack(rows, key) {
				return rows.map(function(row) { return row[key]; });
			}

			var data = [];
			var scl =['rgb(213,62,79)','rgb(244,109,67)','rgb(253,174,97)','rgb(254,224,139)','rgb(255,255,191)','rgb(230,245,152)','rgb(171,221,164)','rgb(102,194,165)','rgb(50,136,189)'];
			var allLats = [];
			var allLons = [];

			for ( var i = 0 ; i < scl.length; i++){
				var latHead = 'lat-'+i;
				var lonHead = 'lon-'+i;
				var lat = unpack(rows, latHead);
				var lon = unpack(rows, lonHead);
				allLats.push(lat);
				allLons.push(lon);
			}
			for ( var i = 0 ; i < scl.length; i++) {
				var current = {
					type:'scattergeo',
					lon: allLons[i],
					lat: allLats[i],
					mode: 'lines',
					line: {
						width: 2,
						color: scl[i]
					}
				}
				data.push(current);
			};
			var layout = {
				geo: {
					projection: {
						type: 'orthographic',
						rotation: {
							lon: -100,
							lat: 40
						},
					},
					showocean: true,
					oceancolor: 'rgb(0, 255, 255)',
					showland: true,
					landcolor: 'rgb(230, 145, 56)',
					showlakes: true,
					lakecolor: 'rgb(0, 255, 255)',
					showcountries: true,
					lonaxis: {
						showgrid: true,
						gridcolor: 'rgb(102, 102, 102)'
					},
					lataxis: {
						showgrid: true,
						gridcolor: 'rgb(102, 102, 102)'
					}
				}
			};
			Plotly.plot(this.$refs.map, data, layout, {showLink: false});
		});*/

        /*  Fully Styled Box Plot  */
        ;(() => {
            var xData = [
                "Carmelo<br>Anthony",
                "Dwyane<br>Wade",
                "Deron<br>Williams",
                "Brook<br>Lopez",
                "Damian<br>Lillard",
                "David<br>West",
                "Blake<br>Griffin",
                "David<br>Lee",
                "Demar<br>Derozan"
            ]

            function getrandom(num, mul) {
                var value = []
                for (i = 0; i <= num; i++) {
                    var rand = Math.random() * mul
                    value.push(rand)
                }
                return value
            }

            var yData = [
                getrandom(30, 10),
                getrandom(30, 20),
                getrandom(30, 25),
                getrandom(30, 40),
                getrandom(30, 45),
                getrandom(30, 30),
                getrandom(30, 20),
                getrandom(30, 15),
                getrandom(30, 43)
            ]
            var colors = [
                "rgba(93, 164, 214, 0.5)",
                "rgba(255, 144, 14, 0.5)",
                "rgba(44, 160, 101, 0.5)",
                "rgba(255, 65, 54, 0.5)",
                "rgba(207, 114, 255, 0.5)",
                "rgba(127, 96, 0, 0.5)",
                "rgba(255, 140, 184, 0.5)",
                "rgba(79, 90, 117, 0.5)",
                "rgba(222, 223, 0, 0.5)"
            ]

            var data = []

            for (var i = 0; i < xData.length; i++) {
                var result = {
                    type: "box",
                    y: yData[i],
                    name: xData[i],
                    boxpoints: "all",
                    jitter: 0.5,
                    whiskerwidth: 0.2,
                    fillcolor: "cls",
                    marker: {
                        size: 2
                    },
                    line: {
                        width: 1
                    }
                }
                data.push(result)
            }

            var layout = {
                title: "Points Scored by the Top 9 Scoring NBA Players in 2012",
                yaxis: {
                    autorange: true,
                    showgrid: true,
                    zeroline: true,
                    dtick: 5,
                    gridcolor: "rgb(255, 255, 255)",
                    gridwidth: 1,
                    zerolinecolor: "rgb(255, 255, 255)",
                    zerolinewidth: 2
                },
                margin: {
                    l: 40,
                    r: 30,
                    b: 80,
                    t: 100
                },
                //paper_bgcolor: 'rgb(243, 243, 243)',
                //splot_bgcolor: 'rgb(243, 243, 243)',
                showlegend: false
            }

            Plotly.newPlot(this.$refs.boxPlot, data, layout)
        })()

        /*  Time Series with Rangeslider  */
        Plotly.d3.csv(
            "https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv",
            (err, rows) => {
                function unpack(rows, key) {
                    return rows.map(function (row) {
                        return row[key]
                    })
                }

                var trace1 = {
                    type: "scatter",
                    mode: "lines",
                    name: "AAPL High",
                    x: unpack(rows, "Date"),
                    y: unpack(rows, "AAPL.High"),
                    line: { color: "#17BECF" }
                }
                var trace2 = {
                    type: "scatter",
                    mode: "lines",
                    name: "AAPL Low",
                    x: unpack(rows, "Date"),
                    y: unpack(rows, "AAPL.Low"),
                    line: { color: "#7F7F7F" }
                }

                var data = [trace1, trace2]

                var layout = {
                    title: "Time Series with Rangeslider",
                    xaxis: {
                        autorange: true,
                        range: ["2015-02-17", "2017-02-16"],
                        rangeselector: {
                            buttons: [
                                {
                                    count: 1,
                                    label: "1m",
                                    step: "month",
                                    stepmode: "backward"
                                },
                                {
                                    count: 6,
                                    label: "6m",
                                    step: "month",
                                    stepmode: "backward"
                                },
                                { step: "all" }
                            ]
                        },
                        rangeslider: { range: ["2015-02-17", "2017-02-16"] },
                        type: "date"
                    },
                    yaxis: {
                        autorange: true,
                        range: [86.8700008333, 138.870004167],
                        type: "linear"
                    }
                }

                Plotly.newPlot(this.$refs.time, data, layout)
            }
        )

        /*  Wind Rose Chart  */
        var trace1 = {
            r: [77.5, 72.5, 70.0, 45.0, 22.5, 42.5, 40.0, 62.5],
            t: ["North", "N-E", "East", "S-E", "South", "S-W", "West", "N-W"],
            name: "11-14 m/s",
            marker: { color: "rgb(106,81,163)" },
            type: "area"
        }

        var trace2 = {
            r: [57.5, 50.0, 45.0, 35.0, 20.0, 22.5, 37.5, 55.0],
            t: ["North", "N-E", "East", "S-E", "South", "S-W", "West", "N-W"],
            name: "8-11 m/s",
            marker: { color: "rgb(158,154,200)" },
            type: "area"
        }

        var trace3 = {
            r: [40.0, 30.0, 30.0, 35.0, 7.5, 7.5, 32.5, 40.0],
            t: ["North", "N-E", "East", "S-E", "South", "S-W", "West", "N-W"],
            name: "5-8 m/s",
            marker: { color: "rgb(203,201,226)" },
            type: "area"
        }

        var trace4 = {
            r: [20.0, 7.5, 15.0, 22.5, 2.5, 2.5, 12.5, 22.5],
            t: ["North", "N-E", "East", "S-E", "South", "S-W", "West", "N-W"],
            name: "< 5 m/s",
            marker: { color: "rgb(242,240,247)" },
            type: "area"
        }

        var data = [trace1, trace2, trace3, trace4]

        var layout = {
            title: "Wind Speed Distribution in Laurel, NE",
            font: { size: 16 },
            legend: { font: { size: 16 } },
            radialaxis: { ticksuffix: "%" },
            orientation: 270,
            width: 340
        }

        Plotly.newPlot(this.$refs.polar, data, layout)
    }
})
</script>

<style lang="scss"></style>
