<template>
	<div class="page">
		<div class="card-row flex flex-wrap">
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardExtra1 class="h-full" title="Card with tabs" />
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardExtra2 class="h-full" />
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardExtra5 class="h-full" hideImage />
			</div>
		</div>
		<div class="card-row flex flex-wrap">
			<div class="card-wrap lg:basis-2/3 basis-full">
				<CardWrapper v-slot="{ expand, reload }" class="h-full">
					<CardExtra6 class="h-full" @expand="expand" @reload="reload" :tableRows="6" />
				</CardWrapper>
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full flex flex-col">
				<CardExtra3 />
				<CardExtra4 class="h-full" />
			</div>
		</div>
		<div class="card-row flex flex-wrap">
			<div class="card-wrap lg:basis-2/3 basis-full">
				<CardExtra7 class="h-full" />
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full flex flex-col">
				<CardSocial1 :like="true" class="h-full" />
			</div>
		</div>
		<div class="card-row flex flex-wrap">
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardSocial1 :showImage="true" :showComments="true" />
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardSocial1 :showImage="false" :showComments="true" :like="true" />
			</div>
			<div class="card-wrap lg:basis-1/3 basis-full">
				<CardSocial1 :hideText="true" :showImage="true" :like="true" />
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
.page {
	--card-gap: 0.625em;
	.card-row {
		margin-left: calc(var(--card-gap) * -1);
		margin-right: calc(var(--card-gap) * -1);

		.card-wrap {
			padding: var(--card-gap);

			&.flex-col {
				gap: calc(var(--card-gap) * 2);
			}
		}
	}
}
</style>
