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
                <i v-if="item.health === IndexHealth.GREEN" class="mdi mdi-shield-check"></i>
                <i v-else-if="item.health === IndexHealth.YELLOW" class="mdi mdi-alert"></i>
                <i v-else-if="item.health === IndexHealth.RED" class="mdi mdi-alert-decagram"></i>
                {{ item.index }}
            </span>
        </Vue3Marquee>
        <div class="info"><i class="mdi mdi-information-outline"></i> Click on an index to select</div>
    </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { Index, IndexHealth } from "@/types/indices.d"
import { Vue3Marquee } from "vue3-marquee"

const emit = defineEmits<{
    (e: "click", value: Index): void
}>()

const props = defineProps<{
    indices: Index[]
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value.length === 0)
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
            }
            &.red {
                color: $text-color-danger;
            }
        }
    }
}
</style>
