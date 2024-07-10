<template>
	<div class="flex items-center search-btn" @click="openBox">
		<Icon :name="SearchIcon" :size="16" class="search-btn-icon"></Icon>
		<span>Search</span>
		<n-text code class="search-command">
			<span :class="{ win: commandIcon === 'CTRL' }">{{ commandIcon }}</span>
			K
		</n-text>
	</div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from "vue"
import { NText } from "naive-ui"
import { getOS } from "@/utils"
import Icon from "@/components/common/Icon.vue"
import { useSearchDialog } from "@/composables/useSearchDialog"

const SearchIcon = "ion:search-outline"
const commandIcon = ref("⌘")

function openBox() {
	useSearchDialog().open()
}

onMounted(() => {
	const isWindows = getOS() === "Windows"
	commandIcon.value = isWindows ? "CTRL" : "⌘"
})
</script>

<style lang="scss" scoped>
.search-btn {
	border-radius: 50px;
	background-color: var(--bg-body);
	gap: 10px;
	height: 32px;
	cursor: pointer;
	padding: 4px 10px;
	padding-right: 6px;
	outline: none;
	border: none;

	.search-command {
		white-space: nowrap;

		span {
			line-height: 0;
			position: relative;
			top: 1px;
			font-size: 16px;

			&.win {
				font-size: inherit;
				top: 0;
			}
		}
	}

	:deep() {
		& > .n-icon {
			opacity: 0.5;
			transition: opacity 0.3s;
		}
	}
	& > span {
		opacity: 0.5;
		padding-right: 2px;
		font-size: 14px;
		transition: opacity 0.3s;
	}

	:deep() {
		& > code {
			background-color: var(--hover-005-color);
			border-top-right-radius: 10px;
			border-bottom-right-radius: 10px;
			padding-right: 10px;
		}
	}

	&:hover {
		:deep() {
			& > .n-icon {
				opacity: 0.9;
			}
		}
		& > span {
			opacity: 0.9;
		}
	}

	@media (max-width: 1000px) {
		padding-right: 8px !important;
		padding-left: 8px !important;

		& > span {
			display: none;
		}
		& > .n-text--code {
			display: none;
		}
	}
}

.direction-rtl {
	.search-btn {
		padding-right: 10px;
		padding-left: 6px;

		.search-btn-icon {
			transform: rotateY(180deg);
		}

		:deep() {
			& > code {
				border-top-left-radius: 10px;
				border-bottom-left-radius: 10px;
				padding-left: 10px;

				border-top-right-radius: var(--n-code-border-radius);
				border-bottom-right-radius: var(--n-code-border-radius);
				padding-right: 0.35em;
			}
		}
	}
}
</style>
