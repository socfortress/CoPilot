<template>
    <span class="input-icon" :class="[`state-${state}`, { color }]">
        <i v-if="state === InputState.RUNNING" class="mdi mdi-shield-check"></i>
    </span>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { RunningInput, InputState } from "@/types/graylog.d"

const props = defineProps<{
    state: RunningInput["state"]
    color?: boolean
}>()
const { state, color } = toRefs(props)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.input-icon {
    &.color {
        &.state-running {
            color: $text-color-success;
        }
        &.state-stopped {
            color: $text-color-danger;
        }
        &.state-paused {
            color: $text-color-warning;
        }
    }
}
</style>
