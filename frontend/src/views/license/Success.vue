<template>
	<div class="page grow flex flex-col">Success</div>
</template>
<script setup lang="ts">
import { useRoute } from "vue-router"

const route = useRoute()

console.log(route.query, route.query.email)
</script>
