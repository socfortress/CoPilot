<template>
	<n-card
		class="card-entity"
		content-class="!p-0"
		:class="[`card-size-${size}`, { embedded, highlighted, clickable, hoverable, disabled }]"
	>
		<n-spin :show="loading">
			<div class="card-entity-wrapper flex flex-col">
				<div class="main-box flex flex-col">
					<div v-if="$slots.header" class="header-box">
						<slot name="header" />
					</div>

					<div
						v-if="!$slots.header && ($slots.headerTitle || $slots.headerExtra)"
						class="header-box flex items-center justify-between"
					>
						<div>
							<slot name="headerTitle" />
						</div>
						<div>
							<slot name="headerExtra" />
						</div>
					</div>

					<div v-if="$slots.default" class="content-box">
						<slot name="default" />
					</div>
				</div>

				<div v-if="$slots.footer" class="footer-box">
					<slot name="footer" />
				</div>

				<div
					v-if="!$slots.footer && ($slots.footerTitle || $slots.footerExtra)"
					class="footer-box flex items-center justify-between"
				>
					<div>
						<slot name="footerTitle" />
					</div>
					<div>
						<slot name="footerExtra" />
					</div>
				</div>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NSpin } from "naive-ui"

const { size, embedded, highlighted, clickable, hoverable, disabled, loading } = defineProps<{
	size?: "medium" | "small" | "large"
	embedded?: boolean
	highlighted?: boolean
	clickable?: boolean
	hoverable?: boolean
	disabled?: boolean
	loading?: boolean
}>()
</script>

<style lang="scss" scoped>
.card-entity {
	transition: all 0.2s var(--bezier-ease);
	overflow: hidden;

	.card-entity-wrapper {
		.main-box {
			@apply gap-3 px-5 py-3;

			.header-box {
				font-family: var(--font-family-mono);
				font-size: 13px;
				color: var(--fg-secondary-color);
			}
			.content-box {
				word-break: break-word;
			}
		}

		.footer-box {
			border-top: var(--border-small-100);
			font-size: 13px;
			background-color: var(--bg-secondary-color);
			@apply gap-3 px-5 py-3;
		}
	}

	&.card-size-small {
		.card-entity-wrapper {
			.main-box,
			.footer-box {
				@apply gap-2 px-3 py-2;
			}
		}
	}

	&.card-size-large {
		.card-entity-wrapper {
			.main-box,
			.footer-box {
				@apply gap-6 px-8 py-6;
			}
		}
	}

	&.clickable {
		@apply cursor-pointer;
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
		border: var(--border-small-100);

		.footer-box {
			background-color: var(--bg-body);
		}
	}

	&.hoverable {
		&:hover {
			box-shadow: 0px 0px 0px 1px var(--primary-040-color);
		}
	}

	&.highlighted {
		box-shadow: 0px 0px 0px 1px var(--primary-color);

		&:hover {
			box-shadow: 0px 0px 0px 2px var(--primary-color);
		}
	}
}
</style>
