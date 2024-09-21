import antfu from "@antfu/eslint-config"

export default antfu({
	vue: true,
	typescript: true,
	javascript: true,
	jsx: true,

	stylistic: {
		indent: "tab",
		quotes: "double"
	},
	rules: {
		"antfu/if-newline": "off",
		"style/operator-linebreak": "off",
		"style/arrow-parens": "off",
		"style/brace-style": "off",
		"style/indent-binary-ops": "off",
		"style/indent": "off",
		"style/member-delimiter-style": "off",
		"style/quotes": "off",
		"style/quote-props": "off",
		"style/eol-last": "off",
		"style/no-mixed-spaces-and-tabs": "off",
		"style/comma-dangle": [
			"error",
			{
				arrays: "never",
				objects: "never",
				imports: "never",
				exports: "never",
				functions: "never"
			}
		],
		"vue/block-order": [
			"error",
			{
				order: ["template", "script", "style"]
			}
		],
		"vue/component-name-in-template-casing": "off",
		"vue/custom-event-name-casing": "off",
		"vue/html-self-closing": "off",
		"vue/singleline-html-element-content-newline": "off",
		"vue/comma-dangle": "off",
		"vue/quote-props": "off"
	}
})
