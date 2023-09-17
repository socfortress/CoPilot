<template>
	<el-dialog
		:show-close="true"
		:class="'user-dialog'"
		v-model="visible"
		@close="$emit('update:dialogvisible', false)"
	>
		<div class="avatar-box">
			<img
				:src="userdata.id ? '/static/images/users/user-' + userdata.id + '.jpg' : imagePlaceholder"
				alt="user avatar"
			/>
			<div class="star" @click="userdata.starred = !userdata.starred">
				<i class="mdi mdi-star align-vertical-middle" v-if="userdata.starred"></i>
				<i class="mdi mdi-star-outline align-vertical-middle" v-if="!userdata.starred"></i>
			</div>
		</div>
		<div class="form-box">
			<el-input placeholder="Fullname" v-model="userdata.full_name"></el-input>
			<el-input placeholder="Email" v-model="userdata.email"></el-input>
			<el-input placeholder="Phone" v-model="userdata.phone"></el-input>
		</div>
	</el-dialog>
</template>

<script>
export default {
	name: "UserDialog",
	props: ["userdata", "dialogvisible"],
	data() {
		return {
			visible: false,
			imagePlaceholder:
				"data:image/jpeg;base64,/9j/4QAYRXhpZgAASUkqAAgAAAAAAAAAAAAAAP/sABFEdWNreQABAAQAAAAeAAD/4QMvaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLwA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/PiA8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjYtYzE0MCA3OS4xNjA0NTEsIDIwMTcvMDUvMDYtMDE6MDg6MjEgICAgICAgICI+IDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+IDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdFJlZj0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlUmVmIyIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOkExM0RGNDdBMzM1QzExRThCNjhCOTFBMEVCQUQzNDYxIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOkExM0RGNDc5MzM1QzExRThCNjhCOTFBMEVCQUQzNDYxIiB4bXA6Q3JlYXRvclRvb2w9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE1IChXaW5kb3dzKSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOkRBMUEyQ0NDMjc2QzExRTg5QUMyOTk2OTcxQkYxODMyIiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOkRBMUEyQ0NEMjc2QzExRTg5QUMyOTk2OTcxQkYxODMyIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+/+4AIUFkb2JlAGTAAAAAAQMAEAMCAwYAAAWZAAAGSQAACC7/2wCEABALCwsMCxAMDBAXDw0PFxsUEBAUGx8XFxcXFx8eFxoaGhoXHh4jJSclIx4vLzMzLy9AQEBAQEBAQEBAQEBAQEABEQ8PERMRFRISFRQRFBEUGhQWFhQaJhoaHBoaJjAjHh4eHiMwKy4nJycuKzU1MDA1NUBAP0BAQEBAQEBAQEBAQP/CABEIAGQAZAMBIgACEQEDEQH/xACdAAEAAgMBAQAAAAAAAAAAAAAABQYBBAcCAwEBAAMBAAAAAAAAAAAAAAAAAAECAwQQAAEEAgMBAQEAAAAAAAAAAAECAwQFEQYAIDAQQBIRAAIBAgMCCwcFAAAAAAAAAAECAxEEACExYRIgMEFRcYGRodFSExBAsSIyQnKSsiMzBRIAAQQDAQEBAAAAAAAAAAAAAQAgMBEQITFxYYH/2gAMAwEAAhEDEQAAAOgAAHzPo09syAAAACF57IRXRjichFq9f9QE/wA24RIAAHLNGyVvpwGbRebPHSPNuFZAAERLfqVa2dct+x1eKmOuOedBy19CsgAY5b1LnOlIUb5ALzSL/nawDDYABjIgIK+L155I3IjS3SlwAAAAAAAAP//aAAgBAgABBQDxQkAEAgjB6JOU8Ucq+gEkIUnhSs8Ukp6NEZ+OEfz0DihwuK4Tny//2gAIAQMAAQUA8VqyQSOA5HRQweJGB9JxwqSeZSOJUD0czj4jOehQk8/hPn//2gAIAQEAAQUA/E9IYjobtqt1Xlsl+mojypcmY7gcodmlVjrbiHW/DZ5SpN590uSp+l8L0EXX3Q0kVfhutWtif8SlS1UNcayr8JjcN6PYaK8lbek3a10+t11Mrw2C+ap482dLsHod/cQkubhfLTJlSZblDtMqucbcQ632up67Gz66NYKehdVAKF9rUmqX0ZZdfd1fXnKlHYgEWOnVUwv6JZoKdKvFGJoSs11RX1iP3f/aAAgBAgIGPwCH6VRRDRgllBaKokDxbYb7mj+N7jcX/9oACAEDAgY/AIrCtpwGWVsLQv2Xkn//2gAIAQEBBj8A9y355FiTzOwUd+NyO8hdjookUn48WFiAe8mr6SnRQNXbBmupWmkP3Ma06BoOr2LFO7TWJNGQmpjHmQnm5sLJGwZHAZWGhBzB4m6LHKJvSQcwQU+NeAI3NTbyNGPxyZf3cTfA5fzue014E7chnNOpV4kf6CLWC5ADkaLIopn+QHtVEBZ2ICqMySdAMQ2rf20Ly087Zns04lob3cMEvylZCADXTXlwX/zZleM5iKXJhsDitevAVxFGvKxevcowk9xKst23ypI9FVSeSNSde/iRQCS6lr6MR0y+5tgwZryUyudK/SuxV0GAkF0+4Mgj0kUdG/WmN311Tasag99cerdSvM/mclqdHNhYLtmmsjka5vHtU82zswskbBkcBlYaEHMHhz3JNVLFYhzRrkvjwpbGQ1NswMdfI9cuog8IqdCKHDSxAzWJzWQZlNknjwVhhQySuaKiipJw9xctW6nUKyKaqig1ptPDIIqDkQcGSCtpKcyY/oJ2ocuymD6E0Mo5K7yH4MO/FCsSjnMnguAb66G7ypCM/wBT+GN2zhCMcmkPzO3Sxz9//9k="
		}
	},
	watch: {
		dialogvisible(val) {
			this.visible = val
		}
	}
}
</script>

<style lang="scss">
@import "../assets/scss/_variables";

.el-dialog.user-dialog {
	max-width: 400px;

	.el-dialog__header {
		padding: 0;

		.el-dialog__headerbtn {
			z-index: 1;
			background: rgba(0, 0, 0, 0.05);
			min-width: 18px;
			min-height: 18px;
			max-width: 18px;
			max-height: 18px;
			border-radius: 4px;
			position: absolute;
			top: 20px;
			right: 20px;

			.el-dialog__close {
				color: $background-color;
			}
		}
	}
	.el-dialog__body {
		padding: 0;
	}

	.avatar-box {
		background: var(--primary-color);
		margin-bottom: 50px;
		position: relative;

		img {
			width: 100px;
			height: 100px;
			border-radius: 50%;
			position: relative;
			bottom: -50px;
			display: block;
			margin: 0 auto;
			background: white;
			border: 2px solid var(--primary-color);
			box-sizing: border-box;
		}

		.star {
			position: absolute;
			top: 50%;
			left: 50%;
			z-index: 1;
			background: white;
			box-sizing: border-box;
			width: 30px;
			height: 30px;
			text-align: center;
			line-height: 28px;
			font-size: 20px;
			border-radius: 50%;
			border: 2px solid var(--primary-color);
			cursor: pointer;
			margin-top: 35px;
			margin-left: 35px;

			.mdi-star {
				color: #ffd730;
			}
			.mdi-star-outline {
				opacity: 0.5;
			}
		}
	}

	.form-box {
		padding: 20px;
		box-sizing: border-box;

		& > * {
			margin: 10px 0;
		}
	}
}
</style>
