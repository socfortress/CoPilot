<template>
    <div class="page-layout-sidebar-left scrollable only-y">
        <div class="page-header header-primary card-base card-shadow--small flex">
            <div class="box grow">
                <h1>Sidebar left</h1>
                <el-breadcrumb separator="/">
                    <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                    <el-breadcrumb-item>UI</el-breadcrumb-item>
                    <el-breadcrumb-item>Layout</el-breadcrumb-item>
                    <el-breadcrumb-item>Sidebar left</el-breadcrumb-item>
                </el-breadcrumb>
            </div>
            <div class="menu-btn align-vertical" @click="sidebarOpen = !sidebarOpen">
                <i class="mdi mdi-menu align-vertical-middle"></i>
            </div>
        </div>
        <div class="flex">
            <div class="sidebar scrollable" :class="{ open: sidebarOpen }">
                <el-button size="small" class="close-btn" @click="sidebarOpen = false">close</el-button>
                <ul>
                    <li v-for="i in 20" :key="i">Sidebar Item {{ i }}</li>
                </ul>
            </div>
            <div class="box grow card-base card-shadow--small p-24">
                <div style="max-width: 1100px; margin: 0 auto">
                    <p class="mt-18">
                        <img src="@/assets/images/photo1.jpg" class="demo-img" alt="demo image" />
                    </p>
                    <h1 class="mt-8">Lorem ipsum dolor sit amet</h1>
                    <p class="mt-0">
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent a odio malesuada, vehicula
                        felis in, porttitor lectus. Donec venenatis nunc metus. Praesent ornare est diam, vitae finibus
                        mauris faucibus quis. Duis magna orci, aliquam at arcu sit amet, sagittis auctor nisi. Aenean
                        vestibulum sem eu orci ultricies, sed accumsan quam varius. Sed vulputate quis orci et ornare.
                        Suspendisse in magna eu felis ullamcorper ultrices.
                    </p>

                    <blockquote>
                        <p>
                            Aliquam et nunc tincidunt, lobortis risus sit amet, tempor dui. Suspendisse potenti.
                            Curabitur gravida feugiat lacinia. Sed blandit, magna ac dictum imperdiet, massa nisl
                            vehicula lorem, vitae fermentum eros orci quis metus. Nam imperdiet enim et velit luctus
                            porttitor. Maecenas in sollicitudin lorem. Curabitur felis ex, gravida ut mauris vitae,
                            faucibus lobortis mauris. Fusce finibus tortor leo, id pharetra magna tincidunt eu. Duis
                            quis nisl malesuada, blandit eros non, auctor velit. Donec accumsan euismod interdum.
                            Pellentesque gravida porta ipsum, hendrerit posuere enim euismod vitae. Nulla luctus
                            lobortis dui, eget rhoncus lacus malesuada id.
                        </p>
                    </blockquote>
                    <p>
                        Integer vestibulum rhoncus erat ac pulvinar. Quisque vitae lectus nec orci tincidunt laoreet.
                        Praesent feugiat orci id dui placerat, ut mattis neque bibendum. Aenean cursus justo ac commodo
                        rhoncus. Etiam vestibulum mollis enim, nec lobortis velit vulputate nec. Proin consequat sapien
                        at nibh aliquet tincidunt. Cras condimentum urna nec justo elementum, vitae congue nulla
                        ullamcorper. Sed ac leo lobortis, feugiat ex sed, gravida enim. Aliquam nec dolor vitae ligula
                        iaculis imperdiet at eget ipsum. Nunc a tincidunt libero, nec maximus felis. Donec sed arcu ac
                        sem imperdiet placerat. Integer fermentum quam eget ex mattis, at scelerisque ante tempor.
                    </p>
                    <p>
                        In eu iaculis ex. Ut tempor dapibus augue, nec mattis ante imperdiet id. Praesent mattis iaculis
                        justo nec fermentum. Nam auctor sagittis euismod. Sed sagittis erat in vulputate iaculis.
                        Maecenas quis purus sit amet orci tempor condimentum a vel purus. Ut hendrerit nulla mi. Nunc
                        condimentum sed libero ut fermentum. Donec varius metus urna, non pretium nulla blandit quis.
                        Aenean vulputate neque eget risus tristique pellentesque. Sed bibendum dolor sit amet lacus
                        vehicula vestibulum. Nullam vel neque pretium metus dapibus aliquam nec at sem.
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "LayoutSidebarLeft",
    data() {
        return {
            sidebarOpen: false
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-layout-sidebar-left {
    padding-left: 20px;
    padding-right: 15px;
    padding-bottom: 20px;

    .page-header {
        margin-bottom: 20px;
        min-height: 60px;

        .menu-btn {
            color: $background-color;
            font-size: 20px;
            display: none;
            cursor: pointer;
        }
    }

    .demo-img {
        width: 100%;
        max-width: 500px;
        margin-bottom: 10px;
        border-radius: 4px;
    }

    .sidebar {
        box-sizing: border-box;
        padding: 24px;
        min-width: 250px;
        margin-left: -24px;

        .close-btn {
            display: none;
            width: 100%;
            margin-bottom: 10px;
        }

        ul {
            width: 100%;
            list-style: none;
            padding: 0;
            margin: 0;
        }
        li {
            box-sizing: border-box;
            width: 100%;
            list-style: none;
            padding: 15px 20px;
            border-bottom: 1px solid transparentize($text-color-primary, 0.9);
            cursor: pointer;
            position: relative;

            &::after {
                content: "";
                display: block;
                width: 0%;
                height: 100%;
                background: $text-color-primary;
                position: absolute;
                top: 0;
                left: 0;
                opacity: 0;
                transition: all 0.5s;
            }

            &:hover {
                &::after {
                    width: 100%;
                    opacity: 0.3;
                }
            }
        }
    }
}

@media (max-width: 768px) {
    .page-layout-sidebar-left {
        padding-left: 5px;
        padding-right: 5px;

        .page-header {
            .menu-btn {
                display: block;
            }
        }
        .sidebar {
            .close-btn {
                display: block;
            }

            margin: 0;
            text-align: center;
            position: absolute;
            background: white;
            color: #000;
            top: 5px;
            left: -100%;
            opacity: 0;
            bottom: 5px;
            box-shadow: 40px 0px 160px 80px rgba(0, 0, 0, 0.3);
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            transition: all 0.5s;

            li {
                border-bottom: 1px solid #eee;
            }

            &.open {
                opacity: 1;
                left: 0;
                z-index: 999;
            }
        }
    }
}
</style>
