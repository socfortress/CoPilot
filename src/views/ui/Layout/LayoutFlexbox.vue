<template>
    <el-scrollbar class="page-layout-flexbox">
        <div class="page-header">
            <h1>Layout Flexbox</h1>
            <h4>
                <a href="https://ixrock.github.io/flexbox/docs/" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <main class="demo-box code1">
            <div class="example">
                <div class="flex gaps auto">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex gaps">
                    <div class="box"></div>
                    <div class="box grow"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example multi-line">
                <div class="flex gaps grid-12">
                    <div class="col-2"></div>
                    <div class="col-2"></div>
                    <div class="col-2"></div>
                    <div class="col-2"></div>
                    <div class="col-2"></div>
                </div>
                <div class="flex gaps grid-12">
                    <div class="col-3"></div>
                    <div class="col-3"></div>
                    <div class="col-3"></div>
                    <div class="col-3"></div>
                </div>
                <div class="flex gaps grid-12">
                    <div class="col-4"></div>
                    <div class="col-4"></div>
                    <div class="col-4"></div>
                </div>
                <div class="flex gaps grid-12">
                    <div class="col-6"></div>
                    <div class="col-6"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex grid-6 gaps custom-gaps">
                    <div class="col-1"></div>
                    <div class="col-2"></div>
                    <div class="col-3"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex column gaps">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box bottom"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex column gaps">
                    <div class="box"></div>
                    <div class="box grow"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex center">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex">
                    <div class="box center left"></div>
                    <div class="box center top"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex">
                    <div class="box"></div>
                    <div class="box center"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex center">
                    <div class="box top left"></div>
                    <div class="box"></div>
                    <div class="box right bottom"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex auto">
                    <div class="box self-flex-start"></div>
                    <div class="box center"></div>
                    <div class="box self-flex-end"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex justify-center align-center">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex justify-space-around">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>

            <div class="example">
                <div class="flex justify-space-between">
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                    <div class="box"></div>
                </div>
            </div>
        </main>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "LayoutFlexbox",
    data() {
        return {}
    },
    mounted() {
        //console.log('LayoutFlexbox mounted')
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.demo-box {
    padding-top: 20px;
    font-size: 13px;
}

main.code1 {
    display: flex;
    flex-flow: row wrap;
    align-items: flex-start;
    margin: 0px -20px;

    & > * {
        flex: 1 0 240px;
        //margin: 30px var(--space);
        margin: 30px 20px;
        position: relative;
        border: 1px solid $text-color-primary;
    }
    .example > .flex {
        min-height: 175px;
    }
    .example.multi-line > .flex {
        min-height: 0;
    }
    .example.multi-line > .flex:not(:last-child) {
        margin-bottom: var(--flex-gap, 1em);
    }
    .example > :after {
        content: 'class="' attr(class) '"';
        position: absolute;
        left: -1px;
        bottom: calc(100% + 1px);
        background: darken($background-color, 10%);
        color: $text-color-primary;
        padding: 0.5rem;
        border: 1px solid $text-color-primary;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border-bottom: 0;
    }
    .flex > * {
        background: darken($background-color, 10%);
        text-align: center;
        padding: 5px;
    }
    .flex > *:after {
        content: attr(class);
    }
    .custom-gaps {
        --flex-gap: 10px;
    }
}
</style>
