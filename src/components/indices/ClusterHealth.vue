<template>
    <div class="cluster-health">
        <div class="title">Overall Health</div>
        <div v-loading="loading">
            <div class="info" v-if="cluster">
                <pre>
					{{ cluster }}
				</pre
                >
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { ClusterHealth, IndexHealth } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"

const cluster = ref<ClusterHealth | null>(null)
const loading = ref(true)

function getClusterHealth() {
    loading.value = true
    Api.indices
        .getClusterHealth()
        .then(res => {
            cluster.value = res.data.cluster_health
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
            loading.value = false
        })
}

onBeforeMount(() => {
    getClusterHealth()
})
</script>
