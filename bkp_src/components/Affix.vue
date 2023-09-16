<template>
    <div class="affix-placeholder" :style="wrapStyle">
        <div :class="{ affix: affixed }" :style="styles">
            <slot></slot>
        </div>
    </div>
</template>
<script>
import { defineComponent } from "vue"

export default defineComponent({
    props: {
        offset: {
            type: Number,
            default: 0
        },
        onAffix: {
            type: Function,
            default() {}
        },
        boundary: {
            type: String,
            default: ""
        },
        scrollerid: {
            type: String,
            default: ""
        }
    },

    data() {
        return {
            scroller: window,
            scrollerIsWindow: true,
            affixed: false,
            styles: {},
            affixedClientHeight: 0,
            affixedClientWidth: 0,
            wrapStyle: {}
        }
    },

    methods: {
        getScroll(w, top) {
            let prop = this.scrollerIsWindow || w === window ? `page${top ? "Y" : "X"}Offset` : `scroll${top ? "Top" : "Left"}`

            return this.scroller[prop]
        },
        getOffset(element) {
            const rect = element.getBoundingClientRect()
            const body = document.body
            //console.log(rect, element.clientTop, body.clientTop)
            const clientTop = element.clientTop || body.clientTop || 0
            const clientLeft = element.clientLeft || body.clientLeft || 0
            //const clientHeight = element.clientHeight || 0;
            const scrollTop = this.getScroll(this.scroller, true)
            const scrollLeft = this.getScroll(this.scroller)
            return {
                top: rect.bottom + scrollTop - clientTop - this.affixedClientHeight,
                left: rect.left + scrollLeft - clientLeft
            }
        },

        handleScroll() {
            const scrollTop = this.getScroll(this.scroller, true) + this.offsets // handle setting offset
            const elementOffset = this.getOffset(this.$el)

            const scrollerOffset = 60

            if (!this.affixed && scrollTop + scrollerOffset > elementOffset.top) {
                this.affixed = true
                this.styles = {
                    top: `${this.offsets + scrollerOffset}px`,
                    left: `${elementOffset.left}px`,
                    width: `${this.$el.offsetWidth}px`
                }
                this.onAffix(this.affixed)
            }

            // if setting boundary
            if (this.boundary && scrollTop > elementOffset.top) {
                const el = window.document.getElementById(this.boundary)
                if (el) {
                    const boundaryOffset = this.getOffset(el)
                    if (scrollTop + this.offsets + scrollerOffset > boundaryOffset.top) {
                        //const top = scrollTop - boundaryOffset.top;
                        const top = boundaryOffset.top - scrollTop
                        this.styles.top = `${top}px`
                    }
                }
            }

            if (this.affixed && scrollTop + scrollerOffset < elementOffset.top) {
                this.affixed = false
                this.styles = {}
                this.onAffix(this.affixed)
            }

            if (this.affixed && this.boundary) {
                const el = window.document.getElementById(this.boundary)
                if (el) {
                    const boundaryOffset = this.getOffset(el)
                    if (scrollTop + this.offsets + scrollerOffset <= boundaryOffset.top) {
                        //this.styles.top = 0 ;
                        this.styles.top = `${0 + scrollerOffset}px`
                    }
                }
            }
        }
    },

    computed: {
        offsets() {
            if (this.boundary) return 0
            return this.offset
        }
    },

    mounted() {
        if (this.scrollerid) {
            this.scrollerIsWindow = false
            this.scroller = window.document.getElementById(this.scrollerid)
        }

        this.affixedClientHeight = this.$el.children[0].clientHeight
        this.affixedClientWidth = this.$el.children[0].clientWidth

        this.wrapStyle = { height: `${this.affixedClientHeight}px`, width: `${this.affixedClientWidth}px` }
        this.scroller.addEventListener("scroll", this.handleScroll)
        this.scroller.addEventListener("resize", this.handleScroll)
    },

    beforeUnmount() {
        this.scroller.removeEventListener("scroll", this.handleScroll)
        this.scroller.removeEventListener("resize", this.handleScroll)
    }
})
</script>
<style lang="scss" scoped>
.affix {
    position: fixed;
}
</style>
