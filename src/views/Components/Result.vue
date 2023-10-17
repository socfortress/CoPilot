<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Result</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/result"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="404">
				<n-result status="404" title="404 Not Found" description="You know life is always ridiculous.">
					<template #footer>
						<n-button>Find Something Funny</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result status="404" title="404 Not Found" description="You know life is always ridiculous.">
						<template #footer>
							<n-button>Find Something Funny</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="403">
				<n-result status="403" title="403 Forbidden" description="Some of the doors are always close to you.">
					<template #footer>
						<n-button>Take It Easy</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result
						status="403"
						title="403 Forbidden"
						description="Some of the doors are always close to you."
					>
						<template #footer>
							<n-button>Take It Easy</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="500">
				<n-result
					status="500"
					title="500 Server Error"
					description="Server error may prove that you need hiring more developers."
				>
					<template #footer>
						<n-button>Speard Money Out</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result
						status="500"
						title="500 Server Error"
						description="Server error may prove that you need hiring more developers."
					>
						<template #footer>
							<n-button>Speard Money Out</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="418">
				<n-result
					status="418"
					title="418 I'm a Teapot"
					description="In Chinese, teapot is a kind of 'Beiju', which means 'tragedy'."
				>
					<template #footer>
						<n-button>It Is Easy to Take the Truth</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result
						status="418"
						title="418 I'm a Teapot"
						description="In Chinese, teapot is a kind of 'Beiju', which means 'tragedy'."
					>
						<template #footer>
							<n-button>It Is Easy to Take the Truth</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Info">
				<n-result
					status="info"
					title="Information"
					description="In this era, info is about money and money is about info."
				>
					<template #footer>
						<n-button>I Want Information</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result
						status="info"
						title="Information"
						description="In this era, info is about money and money is about info."
					>
						<template #footer>
							<n-button>I Want Information</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Success">
				<n-result status="success" title="Success" description="child of failure">
					<template #footer>
						<n-button>I like it</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result status="success" title="Success" description="child of failure">
						<template #footer>
							<n-button>I like it</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Warning">
				<n-result status="warning" title="Warning" description="People seldom see it until it comes true.">
					<template #footer>
						<n-button>Hmm, Truly Sad, Isn't It?</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result status="warning" title="Warning" description="People seldom see it until it comes true.">
						<template #footer>
							<n-button>Hmm, Truly Sad, Isn't It?</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Error">
				<n-result status="error" title="Error" description="It's red">
					<template #footer>
						<n-button>I Don't Like It</n-button>
					</template>
				</n-result>
				<template #code="{ html }">
					{{ html(`
					<n-result status="error" title="Error" description="It's red">
						<template #footer>
							<n-button>I Don't Like It</n-button>
						</template>
					</n-result>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NResult, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
