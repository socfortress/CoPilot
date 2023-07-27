<template>
    <div class="page-vued3network scrollable">
        <div class="page-header">
            <h1>Vue D3 Network</h1>
            <h4>
                <a href="https://github.com/emiliorizzo/vue-d3-network" target="_blank"
                    ><i class="mdi mdi-link-variant"></i>reference</a
                >
            </h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Vue D3 Network</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium">
            <ul class="menu">
                <li>
                    <label> Node size </label>
                    <input type="range" min="1" max="100" v-model="nodeSize" /> {{ options.nodeSize }}
                </li>
                <li>
                    <label>Render as </label>
                    <input type="radio" :value="false" v-model="canvas" />
                    <label>SVG</label>
                    <input type="radio" :value="true" v-model="canvas" />
                    <label>Canvas</label>
                </li>
            </ul>
            <d3-network ref="net" :net-nodes="nodes" :net-links="links" :options="options" />
        </div>
        <div class="card-base card-shadow--medium mt-30">
            <ul class="menu">
                <li>
                    <label>Force: {{ force }}</label>
                    <input type="range" min="-500" max="500" v-model="force" />
                </li>
                <li>
                    <label>Forces X: {{ fX }}</label>
                    <input type="range" min="0" max="1" step=".01" v-model="fX" />
                </li>
                <li>
                    <label>Forces Y: {{ fY }}</label>
                    <input type="range" min="0" max="1" step=".01" v-model="fY" />
                </li>
                <li>
                    <label>Center:</label>
                    <input type="checkbox" v-model="fC" />
                </li>
                <li>
                    <label>Many Body:</label>
                    <input type="checkbox" v-model="fMb" />
                </li>
                <li>
                    <button v-on:click="reset">restart simulation</button>
                </li>
            </ul>
            <d3-network :net-nodes="nodes2" :net-links="[]" :options="options2" />
        </div>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "VueD3NetworkPage",
    data() {
        return {
            nodes: [
                { id: 1, name: "my awesome node 1" },
                { id: 2, name: "my node 2" },
                { id: 3, name: "orange node", _color: "orange" },
                { id: 4, _color: "#0022ff" },
                { id: 5 },
                { id: 6 },
                { id: 7 },
                { id: 8 },
                { id: 9 }
            ],
            links: [
                { sid: 1, tid: 2 },
                { sid: 2, tid: 8 },
                { sid: 3, tid: 4 },
                { sid: 4, tid: 5 },
                { sid: 5, tid: 6 },
                { sid: 7, tid: 8 },
                { sid: 5, tid: 8 },
                { sid: 3, tid: 8 },
                { sid: 7, tid: 9 }
            ],
            nodeSize: 20,
            canvas: false,
            force: 50,
            fX: 0.5,
            fY: 0.5,
            fMb: true,
            fC: false,
            nNodes: 500
        }
    },
    computed: {
        options() {
            return {
                force: 3000,
                //size:{ w:600, h:500},
                nodeSize: this.nodeSize,
                nodeLabels: true,
                canvas: this.canvas
            }
        },
        nodes2() {
            return this.makeNodes()
        },
        options2() {
            return {
                force: this.force,
                forces: {
                    X: this.fX,
                    Y: this.fY,
                    ManyBody: this.fMb,
                    Center: this.fC
                },
                nodeSize: 20,
                nodeLabels: false
            }
        }
    },
    methods: {
        makeNodes() {
            return Array.apply(null, { length: this.nNodes }).map((value, index) => {
                return { id: index, _color: this.randomColor(), _size: Math.random() * 30 }
            })
        },
        reset() {
            this.nNodes++
        },
        randomColor() {
            return "rgb(" + parseInt(Math.random() * 64) + 1 + "," + parseInt(Math.random() * 10) + 1 + "," + 100 + ")"
        }
    }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-vued3network {
    .link-label,
    .node-label {
        fill: $text-color-primary;
    }
    .link {
        stroke: transparentize($text-color-primary, 0.7);
    }
    .node {
        stroke-width: 1;
        stroke: rgba(0, 0, 0, 0.2);
    }
}
</style>
