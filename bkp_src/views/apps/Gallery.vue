<template>
    <div class="page-gallery scrollable only-y">
        <div class="page-header header-accent-gradient card-base card-shadow--small">
            <h1>Gallery</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Apps</el-breadcrumb-item>
                <el-breadcrumb-item>Gallery</el-breadcrumb-item>
            </el-breadcrumb>
            <h4>All pictures taken from <a href="https://pexels.com/" target="_blank" class="white-text">pexels.com</a></h4>
        </div>

        <div class="photo-list">
            <profile-gallery></profile-gallery>
        </div>
    </div>
</template>

<script>
import ProfileGallery from "@/components/Profile/ProfileGallery.vue"

import { defineComponent } from "vue"

export default defineComponent({
    name: "Gallery",
    mounted() {
        //console.log('Gallery mounted')
    },
    components: {
        ProfileGallery
    }
})
</script>

<style lang="scss" scoped>
.page-gallery {
    padding-left: 20px;
    padding-right: 15px;
}
</style>
