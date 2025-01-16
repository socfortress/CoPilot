<template>
	<div class="layout flex">
		<MainContainer class="grow">
			<slot />
		</MainContainer>
	</div>
</template>

<script lang="ts" setup>
import MainContainer from "./MainContainer.vue"
import "./main.scss"
</script>

<style lang="scss" scoped>
.layout {
	width: 100vw;
	height: 100vh;
	height: 100svh;
	overflow: hidden;
	perspective: 1000px;
}
</style>
