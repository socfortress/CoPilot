<template>
    <div class="cluster-health">
        <div class="title">Unhealthy Indices</div>
        <div v-loading="loading">
            <div class="info" v-if="unhealthyIndices.length">
                <div v-for="item of unhealthyIndices" :key="item.index" class="item" :class="item.health" @click="emit('click', item)">
                    <pre>{{ item }}</pre>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { Index, IndexHealth } from "@/types/indices.d"

const emit = defineEmits<{
    (e: "click", value: Index): void
}>()

const props = defineProps<{
    indices: Index[]
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value.length === 0)

const unhealthyIndices = computed(() =>
    indices.value.filter((index: Index) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED)
)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";
</style>
