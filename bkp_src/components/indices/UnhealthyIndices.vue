<template>
    <div class="unhealthy-indices">
        <div class="title">
            Unhealthy Indices <small class="o-050">({{ unhealthyIndices.length }})</small>
        </div>
        <div v-loading="loading">
            <div class="info">
                <template v-if="unhealthyIndices && unhealthyIndices.length">
                    <div
                        v-for="item of unhealthyIndices"
                        :key="item.index"
                        class="item"
                        :class="item.health"
                        @click="emit('click', item)"
                        title="Click for details"
                    >
                        <IndexCard :index="item" />
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { Index, IndexHealth } from "@/types/indices.d"
import IndexCard from "@/components/indices/IndexCard.vue"

const emit = defineEmits<{
    (e: "click", value: Index): void
}>()

const props = defineProps<{
    indices: Index[] | null
}>()
const { indices } = toRefs(props)

const loading = computed(() => !indices?.value || indices.value === null)

const unhealthyIndices = computed(() =>
    (indices.value || []).filter((index: Index) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED)
)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.unhealthy-indices {
    padding: var(--size-5) var(--size-6);
    @extend .card-base;
    @extend .card-shadow--small;

    .title {
        font-size: var(--font-size-4);
        font-weight: var(--font-weight-6);
        margin-bottom: var(--size-5);
    }
    .info {
        min-height: 50px;
        .item {
            cursor: pointer;

            &:not(:last-child) {
                margin-bottom: var(--size-3);
            }
        }
    }
}
</style>
