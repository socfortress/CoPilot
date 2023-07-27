<template>
    <section
        class="ps-container"
        :is="tagname"
        @mouseover.once="update"
        @ps-scroll-y="scrollHanle"
        @ps-scroll-x="scrollHanle"
        @ps-scroll-up="scrollHanle"
        @ps-scroll-down="scrollHanle"
        @ps-scroll-left="scrollHanle"
        @ps-scroll-right="scrollHanle"
        @ps-y-reach-start="scrollHanle"
        @ps-y-reach-end="scrollHanle"
        @ps-x-reach-start="scrollHanle"
        @ps-x-reach-end="scrollHanle"
    >
        <slot></slot>
    </section>
</template>

<script>
import PerfectScrollbar from "perfect-scrollbar"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "vue-ps",
    props: {
        settings: {
            type: Object,
            default: () => ({
                wheelSpeed: 1.5,
                wheelPropagation: true
            })
        },
        swicher: {
            type: Boolean,
            default: true
        },
        tagname: {
            type: String,
            default: "section"
        }
    },
    data() {
        return {
            ps: null,
            _ps_inited: false
        }
    },
    methods: {
        scrollHanle(evt) {
            this.$emit(evt.type, evt)
        },

        update() {
            //this.ps.update(this.$el)
            if (this.ps) this.ps.update()
        },

        __init() {
            this.$nextTick(() => {
                if (this.swicher) {
                    if (!this._ps_inited) {
                        this._ps_inited = true
                        this.ps = new PerfectScrollbar(this.$el, this.settings)
                    } else {
                        this.update(this.$el)
                    }
                }
            })
        },

        __uninit() {
            if (this.ps) this.ps.destroy(this.$el)

            this.ps = null
            this._ps_inited = false
        }
    },

    watch: {
        swicher(val) {
            if (val && !this._ps_inited) {
                this.__init()
            }
            if (!val && this._ps_inited) {
                this.__uninit()
            }
        },

        $route() {
            this.update()
        }
    },

    mounted() {
        // debugger
        this.__init()
    },

    updated() {
        this.$nextTick(this.update)
    },

    activated() {
        this.__init()
    },

    deactivated() {
        this.__uninit()
    },

    beforeUnmount() {
        this.__uninit()
    }
})
</script>

<style lang="scss">
@import "~perfect-scrollbar/css/perfect-scrollbar.css";
.ps-container {
    position: relative;
}
</style>
