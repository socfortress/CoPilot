<template>
    <div class="page-profile-timeline">
        <div class="timeline">
            <div class="time-box" v-for="i in 6" :key="i">
                <div class="time-pin">
                    <div class="avatar">
                        <img src="@/assets/images/avatar.jpg" alt="avatar" />
                    </div>
                </div>
                <div class="time-wrap">
                    <div class="time-content__header">
                        <strong class="username">Aurora Shenton</strong>
                        <span class="time">1{{ i }}/05/2018 22:4{{ i + 2 }}</span>
                    </div>
                    <div class="time-content__content" v-if="i % 2">
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce dictum finibus maximus. Morbi nibh lorem, bibendum
                        porttitor turpis sed, molestie aliquam nibh. Curabitur condimentum ipsum accumsan elementum lobortis. Sed at turpis
                        est. Nam maximus tempor orci ac dictum.
                    </div>
                    <div class="time-content__content" v-else>
                        Donec dapibus molestie lacus ac pellentesque. Quisque imperdiet ultricies elementum. Quisque quis ullamcorper nisl,
                        a facilisis augue. Fusce in lacus dapibus, eleifend orci non, maximus nunc.
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "ProfileTimeline",
    data() {
        return {}
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.page-profile-timeline {
    .timeline {
        font-family: inherit;

        .time-box {
            padding-bottom: 40px;
            overflow: hidden;
            position: relative;

            &:before {
                content: "";
                display: block;
                width: 2px;
                background: $background-color;
                position: absolute;
                top: 0px;
                left: 24px;
                bottom: 0px;
            }

            &:first-child {
                &:before {
                    top: 25px;
                }
            }
            &:last-child {
                &:before {
                    bottom: inherit;
                    height: 15px;
                }
            }

            .time-pin {
                width: 50px;
                height: 50px;
                padding: 5px;
                display: block;
                overflow: hidden;
                float: left;
                box-sizing: border-box;
                position: relative;

                .avatar {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    overflow: hidden;
                    border: 2px solid #fff;
                    box-shadow: 0px 3px 4px -2px rgba(0, 0, 0, 0.4);
                    box-sizing: border-box;

                    img {
                        width: 100%;
                    }
                }
            }

            .time-wrap {
                width: 100%;
                display: block;
                float: right;
                margin-left: -50px;
                padding-left: 60px;
                box-sizing: border-box;

                .time-content__header {
                    font-size: 14px;
                    margin-bottom: 5px;
                    border-bottom: 1px solid transparentize($text-color-primary, 0.8);

                    & > * {
                        margin-right: 10px;
                    }

                    .time {
                        opacity: 0.5;
                    }
                }
            }
        }
    }
}
</style>
