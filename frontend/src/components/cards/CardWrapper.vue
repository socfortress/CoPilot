<template>
	<div class="card-wrapper">
		<n-spin :show="showSpin" class="h-full">
			<slot :expand="expand" :reload="reload" :isExpand="isExpand"></slot>
		</n-spin>
		<n-modal v-model:show="showModal" display-directive="show" class="card-modal-wrapper">
			<n-spin :show="showSpin">
				<slot :expand="expand" :reload="reload" :isExpand="isExpand"></slot>
			</n-spin>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NModal, NSpin } from "naive-ui"
import { ref } from "vue"

const showModal = ref(false)
const showSpin = ref(false)

function expand(state: boolean): void {
	showModal.value = state
}

function reload(state: boolean): void {
	showSpin.value = state
}

function isExpand(): boolean {
	return showModal.value
}
</script>

<style lang="scss" scoped>
.card-wrapper {
	:deep() {
		.n-spin-content {
			height: 100%;
		}
	}
	.n-card {
		.title {
			line-height: 1.2;
		}
		.subtitle {
			line-height: 1.2;
			font-size: 12px;
			opacity: 0.6;
			margin-top: 10px;
		}

		:deep() {
			.n-spin-content {
				height: 100%;
			}
			.n-card-header {
				align-items: flex-start;
			}
			.n-card__action {
				padding: 0;
			}
		}
	}
}
</style>

<style lang="scss">
.card-modal-wrapper {
	background-color: transparent;
	backdrop-filter: none;
	box-shadow: none !important;

	.n-spin-content {
		margin: 100px 0;
		min-width: 60vw;

		.n-card.n-card--hoverable:hover {
			box-shadow: none;
		}
	}
}
</style>
