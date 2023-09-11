<template>
    <div class="inputs-marquee" v-loading="loading">
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
                v-for="item in parsedItems"
                :key="item.title"
                class="item"
                :class="item.state"
                @click="emit('click', item)"
                title="Click to select"
            >
                <InputIcon :state="item.state" color />
                {{ item.title }}
            </span>
        </Vue3Marquee>
        <div class="info"><i class="mdi mdi-information-outline"></i> Click on an input to select</div>
    </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { RunningInput } from "@/types/graylog.d"
import { Vue3Marquee } from "vue3-marquee"
import InputIcon from "@/components/inputs/InputIcon.vue"

const MIN_ITEMS = 8

const emit = defineEmits<{
    (e: "click", value: RunningInput): void
}>()

const props = defineProps<{
    inputs: RunningInput[] | null
}>()

const { inputs } = toRefs(props)

const parsedItems = computed(() => {
    if (!inputs.value) {
        return []
    }

    if (inputs.value.length >= MIN_ITEMS) {
        return inputs.value
    }

    const list = []
    while (list.length < MIN_ITEMS) {
        list.push(...inputs.value)
    }

    return list
})

const loading = computed(() => !inputs?.value || inputs.value === null)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.inputs-marquee {
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

            &.RUNNING {
                i {
                    color: $text-color-success;
                }
            }
        }
    }
}
</style>
