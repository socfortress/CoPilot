<template>
    <div class="horizontal-nav flex" :class="{ ['pos-' + position]: true }">
        <logo mode="horizontal" />
        <div class="box grow flex nav-container">
            <el-scrollbar class="box grow">
                <Nav @push-page="pushPage" mode="horizontal" />
            </el-scrollbar>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "@vue/runtime-core"
import Nav from "@/core/nav.vue"
import Logo from "@/core/logo.vue"

export default defineComponent({
    name: "HorizontalNav",
    props: ["position"],
    data() {
        return {}
    },
    methods: {
        pushPage(index, indexPath) {
            this.$emit("push-page", { page: index })
        }
    },
    components: {
        Nav,
        Logo
    }
})
</script>

<style lang="scss" scoped>
@import "../assets/scss/_variables";

.horizontal-nav {
    overflow: hidden;
    //overflow-x: scroll;
    //-webkit-overflow-scrolling: touch;
    //-ms-overflow-style: -ms-autohiding-scrollbar;
    background: white;
    height: 45px;
    z-index: 1;
    margin-bottom: 30px;

    &.pos-top {
        border-bottom-left-radius: 16px;
        border-bottom-right-radius: 16px;
    }
    &.pos-bottom {
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
    }

    .nav-container {
        position: relative;
        overflow: hidden;
        padding-right: 20px;

        &::before {
            content: "";
            display: block;
            z-index: 1;
            position: absolute;
            top: 0px;
            left: 0px;
            width: 0px;
            height: 20px;
            box-shadow: 0px 0px 15px 15px #fff;
        }
        &::after {
            content: "";
            display: block;
            z-index: 1;
            position: absolute;
            top: 0px;
            right: 20px;
            width: 0px;
            height: 20px;
            box-shadow: 0px 0px 15px 15px #fff;
        }
    }
}
</style>
