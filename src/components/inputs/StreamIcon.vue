<template>
  <span class="input-icon" :class="[`state-${disabled}`, { color }]">
      <i v-if="disabled === Streams.disabled" class="mdi mdi-shield-check"></i>
  </span>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { Streams } from "@/types/graylog.d"

const props = defineProps<{
  disabled: Streams["disabled"]
  color?: boolean
}>()
const { disabled, color } = toRefs(props)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.input-icon {
  &.color {
      &.state-true {
          color: $text-color-success;
      }
  }
}
</style>
