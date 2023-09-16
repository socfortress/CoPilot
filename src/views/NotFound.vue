<template>
	<div class="page page-wrapped flex items-center justify-center">
		<n-result status="404" title="404 Not Found" size="huge"></n-result>
	</div>
</template>

<script lang="ts" setup>
import { NResult } from "naive-ui"

defineOptions({
	name: "NotFound"
})
</script>

<style lang="scss" scoped>
.page {
	font-size: 300px;
}
</style>
