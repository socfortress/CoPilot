<template>
    <div class="page-markdown scrollable">
        <div class="page-header">
            <h1>Markdown</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Editors</el-breadcrumb-item>
                <el-breadcrumb-item>Markdown</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium">
            <mavon-editor
                v-model="value"
                language="en"
                :toolbars="toolbars"
                :subfield="subfield"
                :defaultOpen="subfield ? null : 'edit'"
            />
        </div>

        <h4>
            <a href="https://github.com/hinesboy/mavonEditor" target="_blank"
                ><i class="mdi mdi-link-variant"></i> reference</a
            >
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"
import "mavon-editor/dist/css/index.css"

export default defineComponent({
    name: "MarkdownPage",
    data() {
        return {
            subfield: true,
            value: `@[toc](toc)

# H1
## H2
### H3
#### H4
##### H5
###### H6

---

Hello world`,
            toolbars: {
                bold: true,
                italic: true,
                header: true,
                underline: true,
                strikethrough: true,
                mark: true,
                superscript: true,
                subscript: true,
                quote: true,
                ol: true,
                ul: true,
                link: true,
                imagelink: true,
                code: true,
                table: true,
                fullscreen: true,
                readmodel: true,
                htmlcode: true,
                help: true,
                /* 1.3.5 */
                undo: true,
                redo: true,
                trash: true,
                save: false,
                /* 1.4.2 */
                navigation: true,
                /* 2.1.8 */
                alignleft: true,
                aligncenter: true,
                alignright: true,
                /* 2.2.1 */
                subfield: true,
                preview: true
            }
        }
    },
    mounted() {
        this.subfield = window.innerWidth >= 340
    }
})
</script>

<style lang="scss">
.page-markdown {
    padding: 0 20px;
}
@media (max-width: 339px) {
    .page-markdown {
        .v-note-wrapper .v-note-op {
            transform: scale(0.8);
            box-shadow: none !important;
        }
    }
}
</style>
