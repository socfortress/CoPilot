<template>
    <el-scrollbar class="page-themes">
        <div class="page-header">
            <h1>Themes</h1>
            <h4>
                <a href="https://pragmatic-docs.vercel.app/#/#/colors" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> read the documentation to create endless
                    combinations</a
                >
            </h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Themes</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div style="margin: 0 -10px">
            <el-row>
                <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                    <a class="theme-link" href="https://pragmatic-theme-a.ddmweb.it/"
                        ><img src="@/assets/images/theme-a.png" alt="theme a image"
                    /></a>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                    <a class="theme-link" href="https://pragmatic-theme-b.ddmweb.it/"
                        ><img src="@/assets/images/theme-b.png" alt="theme b image"
                    /></a>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                    <a class="theme-link" href="https://pragmatic-theme-c.ddmweb.it/"
                        ><img src="@/assets/images/theme-c.png" alt="theme c image"
                    /></a>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                    <a class="theme-link" href="https://pragmatic-theme-d.ddmweb.it/"
                        ><img src="@/assets/images/theme-d.png" alt="theme d image"
                    /></a>
                </el-col>
            </el-row>
        </div>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Themes"
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.page-themes {
    .theme-link {
        display: block;
        padding: 10px;
        box-sizing: border-box;

        img {
            width: 100%;
            border-radius: 10px;
            box-sizing: border-box;
            border: 3px solid white;
            box-shadow: 0px 7px 20px -7px rgba(0, 0, 0, 0.55);
            transition: all 0.5s;
        }

        &:hover {
            img {
                transform: translateY(5px);
                box-shadow: none;
            }
        }
    }
}
</style>
