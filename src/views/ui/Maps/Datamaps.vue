<template>
    <div class="page-datamaps scrollable">
        <div class="page-header">
            <h1>Datamaps</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Maps</el-breadcrumb-item>
                <el-breadcrumb-item>Datamaps</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium">
            <div id="container" style="position: relative; width: 100%; max-width: 800px; height: 500px; margin: 0 auto"></div>
        </div>

        <h4>
            <a href="https://github.com/markmarkoh/datamaps" target="_blank"><i class="mdi mdi-link-variant"></i> reference</a>
        </h4>
    </div>
</template>

<script>
import Datamap from "datamaps"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "DatamapsPage",
    data() {
        return {}
    },
    mounted() {
        const basic_choropleth = new Datamap({
            element: document.getElementById("container"),
            projection: "mercator",
            fills: {
                defaultFill: "#ABDDA4",
                authorHasTraveledTo: "#fa0fa0"
            },
            data: {
                USA: { fillKey: "authorHasTraveledTo" },
                JPN: { fillKey: "authorHasTraveledTo" },
                ITA: { fillKey: "authorHasTraveledTo" },
                CRI: { fillKey: "authorHasTraveledTo" },
                KOR: { fillKey: "authorHasTraveledTo" },
                DEU: { fillKey: "authorHasTraveledTo" }
            }
        })

        const colors = d3.scale.category10()

        setInterval(() => {
            basic_choropleth.updateChoropleth({
                USA: colors(Math.random() * 10),
                RUS: colors(Math.random() * 100),
                AUS: { fillKey: "authorHasTraveledTo" },
                BRA: colors(Math.random() * 50),
                CAN: colors(Math.random() * 50),
                ZAF: colors(Math.random() * 50),
                IND: colors(Math.random() * 50)
            })
        }, 2000)
    }
})
</script>

<style lang="scss">
.datamaps-hoverover {
    color: black;
}
</style>
