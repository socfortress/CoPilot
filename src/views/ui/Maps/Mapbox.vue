<template>
    <div class="page-mapbox scrollable ph-20">
        <div class="page-header">
            <h1>Mapbox</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Maps</el-breadcrumb-item>
                <el-breadcrumb-item>Mapbox</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium" v-loading="loading">
            <div id="map" v-if="!loading"></div>
        </div>

        <h4>
            <a href="https://www.mapbox.com/mapbox-gl-js/api" target="_blank"> <i class="mdi mdi-link-variant"></i> reference </a>
        </h4>
    </div>
</template>

<script>
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "MapboxPage",
    data() {
        return {
            innerWidth: 0,
            dragging: true,
            loading: false,
            map: null
        }
    },
    watch: {
        dragging(val) {
            this.loading = true
            setTimeout(() => {
                this.loading = false
                setTimeout(() => {
                    this.initMap()
                }, 500)
            }, 500)
        }
    },
    methods: {
        initMap() {
            if (!this.loading) {
                mapboxgl.accessToken = "pk.eyJ1IjoibGlua28iLCJhIjoiY2pmZWFoMG1iMHdzeDMzcGtrY3h4cXdjOSJ9.Ad6zNqdn5Ju_sx6a2RUXRA"
                this.map = new mapboxgl.Map({
                    container: "map",
                    style: "mapbox://styles/mapbox/streets-v9",
                    dragPan: this.dragging
                })
            }
        },
        setDragging() {
            this.innerWidth = window.innerWidth
            if (window.innerWidth <= 768) this.dragging = false
            else this.dragging = true
        }
    },
    created() {
        this.setDragging()
        window.addEventListener("resize", this.setDragging)
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.setDragging)
    },
    mounted() {
        this.initMap()
    }
})
</script>

<style lang="scss" scoped>
#map {
    width: 100%;
    height: 500px;
}
</style>
