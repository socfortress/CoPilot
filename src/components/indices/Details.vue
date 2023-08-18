<template>
    <div class="index-details-box" v-loading="loading" :class="{ active: currentIndex }">
        <div class="box-header">
            <div class="title">
                <span v-if="currentIndex"> Below the details for index </span>
                <span v-else> Select an index to see the details </span>
            </div>
            <div class="select-box">
                <el-select v-model="currentIndex" placeholder="Index list" clearable value-key="index" filterable>
                    <el-option v-for="index in indices" :key="index.index" :label="index.index" :value="index"></el-option>
                </el-select>
            </div>
        </div>
        <div class="details-box" v-if="currentIndex">
            <div class="info">
                <pre> {{ currentIndex }} </pre>
            </div>
            <div class="shards">
                <pre>{{ filteredShards }}</pre>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { Index, IndexHealth, IndexShard } from "@/types/indices.d"
import { ElMessage } from "element-plus"
import Api from "@/api"

type IndexModel = Index | null | ""

const emit = defineEmits<{
    (e: "update:modelValue", value: IndexModel): void
}>()

const props = defineProps<{
    indices: Index[]
    modelValue: IndexModel
}>()
const { indices, modelValue } = toRefs(props)

const shards = ref<IndexShard[]>([])
const loadingShards = ref(false)
const loading = computed(() => !indices?.value || indices.value.length === 0 || loadingShards.value)
// TODO: test multishards with "wazuh_00001_92" index
const filteredShards = computed(() =>
    shards.value.filter((shard: IndexShard) => {
        if (!currentIndex.value || typeof currentIndex.value === "string") return false
        return shard.index === currentIndex.value?.index
    })
)

const currentIndex = computed<IndexModel>({
    get() {
        return modelValue.value
    },
    set(value) {
        emit("update:modelValue", value)
    }
})

function getShards() {
    loadingShards.value = true
    Api.indices
        .getShards()
        .then(res => {
            shards.value = res.data.shards
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                    type: "error"
                })
            } else if (err.response.status === 404) {
                ElMessage({
                    message: "No alerts were found.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingShards.value = false
        })
}

onBeforeMount(() => {
    getShards()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.index-details-box {
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
            margin-right: 20px;
        }

        .select-box {
            .el-select {
                min-width: 350px;
            }
        }
    }
}
</style>
