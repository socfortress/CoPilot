<template>
	<div class="page">
		<FileAnalysisJobDetail :job-id :batch-ids />
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useRoute } from "vue-router"
import FileAnalysisJobDetail from "@/components/fileAnalysis/FileAnalysisJobDetail.vue"

const route = useRoute()

const jobId = computed(() => (route.params.jobId as string) || "")

// A batch of files analyzed together (via ?batch=id1,id2,…) shows a sidebar to flip
// between them, so analyzing N files doesn't hide N-1 of the results.
const batchIds = computed(() =>
	((route.query.batch as string) || "")
		.split(",")
		.map(s => s.trim())
		.filter(Boolean)
)
</script>
