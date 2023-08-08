<template>
    <span></span>
</template>

<script>
import Peity from "./lib/peity"

const types = ["line", "bar", "pie", "donut"]

import { defineComponent } from "vue"

export default defineComponent({
    props: {
        type: {
            type: String,
            required: true,
            validator: value => types.indexOf(value) > -1
        },
        data: {
            type: String,
            required: true
        },
        options: {
            type: Object,
            default: () => ({})
        }
    },
    data() {
        return {
            chart: null
        }
    },
    mounted() {
        this.chart = new Peity(this.$el, this.type, this.data, this.options)
        this.chart.draw()
    },
    watch: {
        data(val) {
            this.$nextTick(() => {
                this.chart.raw = val
                this.chart.draw()
            })
        }
    }
})
</script>
