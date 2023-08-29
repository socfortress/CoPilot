<template>
    <div class="indices-marquee" v-loading="loading">
        <Vue3Marquee
            class="marquee-wrap"
            :duration="200"
            :pauseOnHover="true"
            :clone="true"
            :gradient="true"
            :gradient-color="[255, 255, 255]"
            gradient-length="10%"
        >
            <span
                v-for="item in indices"
                :key="item.index"
                class="item"
                :class="item.health"
                @click="emit('click', item)"
                title="Click to select"
            >
                <IndexIcon :health="item.health" color />
                {{ item.index }}
            </span>
        </Vue3Marquee>
        <div class="info"><i class="mdi mdi-information-outline"></i> Click on an index to select</div>
    </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { Index } from "@/types/indices.d"
import { Vue3Marquee } from "vue3-marquee"
import IndexIcon from "@/components/indices/IndexIcon.vue"

const emit = defineEmits<{
    (e: "click", value: Index): void
}>()

const props = defineProps<{
    indices: Index[] | null
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value === null)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.indices-marquee {
    .info {
        opacity: 0.5;
        font-size: 12px;
        margin-top: 5px;
    }
    .marquee-wrap {
        height: 45px;
        transform: translate3d(0, 0, 0);
        @extend .card-base;

        :deep() {
            .marquee {
                transform: translate3d(0, 0, 0);
            }
            .overlay {
                &:after {
                    right: -1px;
                }
            }
        }

        .item {
            padding: 10px 20px;
            cursor: pointer;

            &.green {
                i {
                    color: $text-color-success;
                }
            }
            &.yellow {
                color: $text-color-warning;
                font-weight: bold;
            }
            &.red {
                color: $text-color-danger;
                font-weight: bold;
            }
        }
    }
}
</style>
