import type { FlaskBaseResponse } from "@/types/flask"
import type { AxiosResponse } from "axios"
import Api from "@/api"
import { acceptHMRUpdate, defineStore } from "pinia"

export const useCaseReportTemplateStore = defineStore("caseReportTemplate", {
	state: () => ({
		templatesList: [] as string[],
		checkedAt: 0,
		loading: false
	}),
	actions: {
		init() {
			if (!this.checkedAt && !this.loading) {
				this.refreshTemplates()
			}
		},
		setTemplatesList(templatesList: string[]) {
			this.templatesList = templatesList
			this.checkedAt = new Date().getTime()
		},
		addTemplate(templateName: string) {
			this.templatesList.push(templateName)
			this.checkedAt = new Date().getTime()
		},
		removeTemplate(templateName: string) {
			this.templatesList = this.templatesList.filter(o => o !== templateName)
			this.checkedAt = new Date().getTime()
		},
		setLoading(value: boolean) {
			this.loading = value
		},
		refreshTemplates(): Promise<AxiosResponse<FlaskBaseResponse>> {
			return new Promise((resolve, reject) => {
				this.setLoading(true)

				Api.incidentManagement
					.getCaseReportTemplate()
					.then(res => {
						if (res.data.success) {
							this.setTemplatesList(res.data.case_report_template_data_store)
							resolve(res)
						} else {
							reject(res)
						}
					})
					.catch(err => {
						reject(err)
					})
					.finally(() => {
						this.setLoading(false)
					})
			})
		},
		uploadCustomTemplate(file: File): Promise<AxiosResponse<FlaskBaseResponse>> {
			return new Promise((resolve, reject) => {
				Api.incidentManagement
					.uploadCustomCaseReportTemplate(file)
					.then(res => {
						if (res.data.success) {
							this.addTemplate(res.data.case_report_template_data_store.file_name)
							resolve(res)
						} else {
							reject(res)
						}
					})
					.catch(err => {
						reject(err)
					})
			})
		},
		deleteTemplate(templateName: string): Promise<AxiosResponse<FlaskBaseResponse>> {
			return new Promise((resolve, reject) => {
				Api.incidentManagement
					.deleteCaseReportTemplate(templateName)
					.then(res => {
						if (res.data.success) {
							this.removeTemplate(templateName)
							resolve(res)
						} else {
							reject(res)
						}
					})
					.catch(err => {
						reject(err)
					})
			})
		}
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useCaseReportTemplateStore, import.meta.hot))
}
