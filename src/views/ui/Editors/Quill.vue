<template>
    <div class="page-quill scrollable">
        <div class="page-header">
            <h1>Quill</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Editors</el-breadcrumb-item>
                <el-breadcrumb-item>Quill</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <h2 class="mt-60">Theme Snow</h2>
        <div class="card-base card-shadow--medium" style="min-height: 300px">
            <vue-quill-editor
                v-model="content1"
                ref="myQuillEditor1"
                :options="editorOption1"
                @blur="onEditorBlur($event)"
                @focus="onEditorFocus($event)"
                @ready="onEditorReady($event)"
            >
            </vue-quill-editor>
        </div>

        <h2 class="mt-60">Theme Bubble</h2>
        <div class="card-base card-shadow--medium p-40 pb-200 t-bubble" id="t-bubble">
            <vue-quill-editor
                v-model="content2"
                ref="myQuillEditor2"
                :options="editorOption2"
                @blur="onEditorBlur($event)"
                @focus="onEditorFocus($event)"
                @ready="onEditorReady($event)"
            >
            </vue-quill-editor>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"
import VueQuillEditor from "@/components/vue-quill-editor.vue"

export default defineComponent({
    name: "QuillPage",
    data() {
        return {
            content1: "<h2>I am Example</h2>",
            editorOption1: {
                theme: "snow"
            },
            content2: "<h2>I am Example</h2>",
            editorOption2: {
                bounds: "#t-bubble",
                theme: "bubble",
                modules: {
                    toolbar: [["bold", "italic", "underline", "strike"], [{ header: [1, 2, 3, 4, 5, 6, false] }]]
                }
            }
        }
    },
    methods: {
        onEditorBlur(quill) {
            console.log("editor blur!", quill)
        },
        onEditorFocus(quill) {
            console.log("editor focus!", quill)
        },
        onEditorReady(quill) {
            console.log("editor ready!", quill)
        },
        onEditorChange({ quill, html, text }) {
            console.log("editor change!", quill, html, text)
            this.content = html
        }
    },
    computed: {
        editor() {
            return this.$refs.myQuillEditor1.quill
        }
    },
    mounted() {
        console.log("this is current quill instance object", this.editor)
    },
    components: { VueQuillEditor }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-quill {
    padding: 0 20px;
    padding-bottom: 20px;

    .card-base {
        box-sizing: border-box;

        .quill-editor {
            .ql-toolbar.ql-snow {
                border: none;
                background: lighten($background-color, 2%);
                border-bottom: 1px solid $background-color;
            }
            .ql-container.ql-snow {
                border: none;
            }
        }

        &.t-bubble {
            overflow: inherit;
        }
    }
}

@media (max-width: 768px) {
    .page-quill {
        .card-base {
            &.t-bubble {
                padding: 40px 20px;
            }
        }
    }
}
</style>
