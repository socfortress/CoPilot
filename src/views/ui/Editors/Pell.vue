<template>
    <div class="page-quill scrollable">
        <div class="page-header">
            <h1>Pell</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Editors</el-breadcrumb-item>
                <el-breadcrumb-item>Pell</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium">
            <VuePellEditor
                :actions="editorOptions"
                :content="editorContent"
                :placeholder="editorPlaceholder"
                v-model="editorContent"
                :styleWithCss="false"
                editorHeight="400px"
            />
        </div>

        <h4>
            <a href="https://github.com/CinKon/vue-pell-editor" target="_blank"><i class="mdi mdi-link-variant"></i> reference</a>
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"
import VuePellEditor from "@/components/VuePellEditor.vue"

export default defineComponent({
    name: "PellPage",
    data() {
        return {
            editorContent: "",
            editorOptions: [
                "bold",
                "underline",
                {
                    name: "italic",
                    result: () => window.pell.exec("italic")
                },
                {
                    name: "custom",
                    icon: "<b><u><i>C</i></u></b>",
                    title: "Custom Action",
                    result: () => console.log("YOLO")
                },
                {
                    name: "image",
                    result: () => {
                        const url = window.prompt("Enter the image URL")
                        if (url) window.pell.exec("insertImage", ensureHTTP(url))
                    }
                },
                {
                    name: "link",
                    result: () => {
                        const url = window.prompt("Enter the link URL")
                        if (url) window.pell.exec("createLink", ensureHTTP(url))
                    }
                }
            ],
            editorPlaceholder: "Write something amazing...",
            editorContent: "<div>Predefined Content</div>"
        }
    },
    components: { VuePellEditor }
})
</script>

<style lang="scss"></style>
