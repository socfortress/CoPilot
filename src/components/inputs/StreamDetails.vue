<template>
    <div class="stream-details-box" v-loading="loading" :class="{ active: currentStream }">
        <div class="box-header">
            <div class="title">
                <span v-if="currentStream"> Below the details for stream </span>
                <span v-else> Select a stream to see the details </span>
            </div>
            <div class="select-box" v-if="streams && streams.length">
                <el-select v-model="currentStream" placeholder="Streams list" clearable value-key="stream" filterable>
                    <el-option v-for="stream in streams" :key="stream.id" :label="stream.title" :value="stream"></el-option>
                </el-select>
            </div>
        </div>
        <div class="details-box" v-if="currentStream">
            <div class="info">
                <StreamCard :stream="currentStream" showActions @delete="clearcurrentStream()" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { Streams } from "@/types/graylog.d"
import { ElMessage } from "element-plus"
import StreamCard from "@/components/inputs/StreamCard.vue"
import Api from "@/api"
import { nanoid } from "nanoid"

type StreamModel = Streams | null | ""

const emit = defineEmits<{
    (e: "update:modelValue", value: StreamModel): void
}>()

const props = defineProps<{
    streams: Streams[] | null
    modelValue: StreamModel
}>()
const { streams, modelValue } = toRefs(props)

const loading = computed(() => !streams?.value || streams.value === null)

const currentStream = computed<StreamModel>({
    get() {
        return modelValue.value
    },
    set(value) {
        console.log("Setting currentStream:", value) // Debug log
        emit("update:modelValue", value)
    }
})

function clearcurrentStream() {
    currentStream.value = null
}

onBeforeMount(() => {
    // getShards()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.stream-details-box {
    padding: var(--size-5) var(--size-6);
    border: 2px solid transparent;
    @extend .card-base;
    &.active {
        border-color: $text-color-accent;
        @extend .card-shadow--small;
    }

    .box-header {
        display: flex;
        align-items: center;

        .title {
            margin-right: var(--size-4);
        }

        .select-box {
            .el-select {
                min-width: var(--size-fluid-9);
                max-width: 100%;
            }
        }
    }

    .details-box {
        margin-top: var(--size-6);

        .shards {
            margin-top: var(--size-4);
            @extend .card-base;
            @extend .card-shadow--small;

            .shard-state {
                font-weight: bold;
                &.STARTED {
                    color: $text-color-success;
                }
                &.UNASSIGNED {
                    color: $text-color-warning;
                }
            }
        }
    }

    @media (max-width: 1000px) {
        .box-header {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--size-2);
            .select-box {
                width: 100%;
                .el-select {
                    min-width: 100%;
                }
            }
        }
    }
}
</style>
