<template>
    <el-scrollbar class="page-profile" id="affix-container">
        <div class="card-base card-shadow--medium identity" id="boundary">
            <div class="cover"></div>

            <div class="username">
                <div class="cover-small"></div>
                <div class="avatar-small"><img src="@/assets/images/avatar.jpg" alt="avatar" /></div>
                <span>{{ username }}</span>
                <div class="colors-box">
                    <div v-for="i in 5" :key="i" :class="{ color: true, active: colorActive }" :style="{ background: color }"></div>
                </div>
            </div>
            <div class="avatar"><img src="@/assets/images/avatar.jpg" alt="avatar" /></div>
            <img src="@/assets/images/cover-2.jpg" id="color-thief" class="color-thief" alt="profile cover" />
        </div>
        <div class="card-base card-shadow--medium info bg-white black-text">
            <el-tabs v-model="activeTab">
                <el-tab-pane label="Timeline" name="timeline">
                    <profile-timeline></profile-timeline>
                </el-tab-pane>
                <el-tab-pane label="Info" name="info">
                    <profile-edit></profile-edit>
                </el-tab-pane>
                <el-tab-pane label="Photo" name="photo" class="pane-photo">
                    <profile-gallery :boxMargins="false"></profile-gallery>
                </el-tab-pane>
            </el-tabs>
        </div>
    </el-scrollbar>
</template>

<script>
import ProfileEdit from "../../components/Profile/ProfileEdit.vue"
import ProfileGallery from "../../components/Profile/ProfileGallery.vue"
import ProfileTimeline from "../../components/Profile/ProfileTimeline.vue"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Profile",
    data() {
        return {
            username: "Aurora Shenton",
            colorActive: false,
            color: "white",
            activeTab: "timeline",
            affixEnabled: true
        }
    },
    methods: {
        resizeAffixEnabled() {
            if (window.innerWidth <= 768) {
                this.affixEnabled = false
            } else {
                this.affixEnabled = true
            }
        }
    },
    mounted() {
        /*
		var colorThief = new ColorThief();
		setTimeout(()=>{
			let rgb = colorThief.getColor(document.getElementById('color-thief'))
			//console.log('Profile mounted', rgb)
			this.colorActive = true
			this.color = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`
		}, 1000)
		*/

        this.resizeAffixEnabled()
        window.addEventListener("resize", this.resizeAffixEnabled)
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.resizeAffixEnabled)
    },
    components: {
        ProfileEdit,
        ProfileGallery,
        ProfileTimeline
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.page-profile {
    overflow: auto;

    .identity {
        margin-bottom: 20px;
        position: relative;
        width: 100%;
        height: 370px;

        .cover {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url("../../assets/images/cover-2.jpg");
            background-position: 50%;
            background-size: cover;
            background-repeat: no-repeat;
            width: 100%;
            height: 100%;
        }
        .username {
            color: #32325d;
            position: absolute;
            width: 100%;
            height: 50px;
            bottom: 75px;
            left: 0;
            right: 0;
            background: #fff;
            line-height: 50px;
            box-sizing: border-box;
            padding-left: 250px;
            font-size: 25px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            box-shadow:
                0 7px 14px 0 rgba(50, 50, 93, 0.1),
                0 3px 6px 0 rgba(0, 0, 0, 0.07);

            .cover-small {
                width: 220px;
                height: 50px;
                overflow: hidden;
                display: block;
                float: left;
                margin-right: -220px;
                position: relative;
                left: -250px;
                border-radius: 9px;
                -webkit-box-sizing: border-box;
                box-sizing: border-box;
                border: 4px solid white;
                opacity: 0;
                top: 0px;
                background-image: url("../../assets/images/cover-2.jpg");
                background-position: 50%;
                background-size: cover;
                background-repeat: no-repeat;
                -webkit-transition: all 0.5s;
                transition: all 0.5s;
            }
            .avatar-small {
                width: 50px;
                height: 50px;
                overflow: hidden;
                display: block;
                float: left;
                margin-right: -50px;
                position: relative;
                left: -100px;
                border-radius: 50%;
                box-sizing: border-box;
                border: 4px solid white;
                opacity: 0;
                top: 0px;
                transform: rotate(-50deg);
                transition: all 0.5s;
            }
            .avatar-small img {
                width: 100%;
            }

            &.affix {
                z-index: 99;
                border-radius: 5px;

                .cover-small {
                    opacity: 1;
                }

                .avatar-small {
                    opacity: 1;
                    left: -60px;
                    transform: rotate(0deg);
                }
            }

            .colors-box {
                height: 50px;
                background: white; //091c2d
                float: right;

                .color {
                    width: 50px;
                    height: 50px;
                    background: white; //091c2d
                    float: right;
                    transform: skew(-45deg);
                    box-shadow: 1px 0px 1px 0px transparent;
                    position: relative;
                    right: -25px;
                    margin-right: -50px;
                    transition: margin-right 0.75s;

                    &.active {
                        margin-right: 0;
                    }

                    &:nth-child(2) {
                        opacity: 0.8;
                    }
                    &:nth-child(3) {
                        opacity: 0.6;
                    }
                    &:nth-child(4) {
                        opacity: 0.4;
                    }
                    &:nth-child(5) {
                        opacity: 0.2;
                    }
                }
            }
        }
        .avatar {
            border: 6px solid #fff;
            position: absolute;
            bottom: 10px;
            left: 50px;
            width: 180px;
            height: 180px;
            overflow: hidden;
            border-radius: 50%;
            box-sizing: border-box;
            box-shadow: 0px 20px 15px -15px rgba(0, 0, 0, 0.15);

            img {
                width: 100%;
            }
        }

        .color-thief {
            display: block;
            width: 100px;
            visibility: hidden;
            z-index: -999999;
            position: absolute;
        }
    }

    .info {
        padding: 24px 32px;
        margin-bottom: 20px;
    }
}

@media (max-width: 768px) {
    .page-profile {
        .identity {
            height: auto;

            .avatar {
                bottom: inherit;
                top: 10px;
                left: 50%;
                width: 100px;
                margin-left: -50px;
                height: 100px;
                border-width: 3px;
            }

            .username {
                position: inherit;
                padding: 10px;
                margin: 0;
                top: inherit;
                left: inherit;
                z-index: 1;
                right: inherit;
                text-align: center;
                bottom: inherit;
                white-space: inherit;
                line-height: inherit;
                height: auto;
                margin-top: 120px;
                width: 90%;
                margin-left: 5%;
                margin-bottom: 10px;
                border-radius: 50px;

                .colors-box {
                    display: none;
                }

                .avatar-small {
                    display: none;
                }

                .cover-small {
                    display: none;
                }
            }
        }

        .info {
            padding: 8px 16px;
        }
    }
}
</style>

<style lang="scss">
.page-profile {
    .el-tabs:not(.el-tabs--border-card) {
        .el-tabs__item:not(.is-active) {
            color: #32325d;
        }
    }
}
</style>
