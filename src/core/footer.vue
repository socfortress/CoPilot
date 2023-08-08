<template>
    <div class="footer flex align-center justify-space-between" :class="{ above: position === 'above' }">
        <div>
            <a href="https://pragmatic-docs.vercel.app/#/" target="_blank">
                <span class="hidden-xs-only">Documentation</span><span class="hidden-sm-and-up">Docs.</span>
            </a>
        </div>
        <div>
            <span>Made by <a href="https://ddmweb.it" target="_blank">Linko</a></span>
            <a
                class="el-button buy-btn el-button--default el-button--small is-plain"
                href="https://1.envato.market/BkJGL?ref=Linko91&utm_source=pragmaticdemo"
                target="_blank"
            >
                <i class="mdi mdi-cart mr-5"></i> Purchase <span class="hidden-xs-only ml-5">Pragmatic</span>
            </a>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue"
export default defineComponent({
    name: "Footer",
    props: ["position"]
})
</script>

<style lang="scss" scoped>
@import "../assets/scss/_variables";
@import "../assets/scss/_mixins";

.footer {
    width: 100%;
    height: 40px;
    padding: 0 20px;
    box-sizing: border-box;
    background: white;
    margin-top: 2px;
    font-size: 14px;
    border-top-left-radius: 20px;

    &.above {
        box-shadow: 0px 0px 10px 0px rgba(0, 0, 0, 0.08);
        z-index: 1;
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        border-radius: 0;
    }

    a {
        font-weight: bold;
        text-decoration: none;
        color: $text-color-accent;
    }

    .buy-btn {
        margin-left: 10px;
    }
}

@media (max-width: 768px) {
    .footer {
        padding: 0 12px;
        border-radius: 0;
    }
}
</style>
