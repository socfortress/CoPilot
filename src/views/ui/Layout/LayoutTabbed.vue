<template>
    <el-scrollbar class="page-layout-tabbed">
        <div class="page-header header-accent card-base card-shadow--small">
            <h1>Tabbed page</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Tabbed page</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <el-tabs type="border-card">
            <el-tab-pane label="Tab 1">
                <div style="max-width: 1100px; margin: 0 auto" class="pv-20 ph-8">
                    <p class="mt-0">
                        <img src="@/assets/images/photo2.jpg" class="demo-img" alt="demo image" />
                    </p>
                    <h1 style="display: block; clear: both">Tab 1 Lorem ipsum dolor sit amet</h1>
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
            </el-tab-pane>
            <el-tab-pane label="Tab 2">
                <div style="max-width: 1100px; margin: 0 auto" class="pv-20 ph-8">
                    <p class="mt-0">
                        <img src="@/assets/images/photo1.jpg" class="demo-img" alt="demo image" />
                    </p>
                    <h1 style="display: block; clear: both">Tab 2 Lorem ipsum dolor sit amet</h1>
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
            </el-tab-pane>
            <el-tab-pane label="Tab 3">
                <div style="max-width: 1100px; margin: 0 auto" class="pv-20 ph-8">
                    <p class="mt-0">
                        <img src="@/assets/images/photo3.jpg" class="demo-img" alt="demo image" />
                    </p>
                    <h1 style="display: block; clear: both">Tab 3 Lorem ipsum dolor sit amet</h1>
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
            </el-tab-pane>
        </el-tabs>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "LayoutTabbed"
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-layout-tabbed {
    .page-header {
        margin-bottom: 20px;
    }

    .el-tabs {
        border-radius: 5px;
        overflow: hidden;
        color: #000;
    }

    .demo-img {
        width: 100%;
        margin-bottom: 10px;
        border-radius: 4px;
        max-width: 600px;
        float: left;
        margin-right: 35px;
        margin-bottom: 30px;
    }
}
</style>
