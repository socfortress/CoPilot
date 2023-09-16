import bar from "./bar"
import line from "./line"
import pie from "./pie"

const svgElement = (tag, attrs) => {
    let e = document.createElementNS("http://www.w3.org/2000/svg", tag)
    for (let key in attrs) {
        e.setAttribute(key, attrs[key])
    }
    return e
}

// https://gist.github.com/madrobby/3201472
// const svgSupported = ('createElementNS' in document) && svgElement('svg', {}).createSVGRect

class Peity {
    constructor($el, type, data, options) {
        this.$el = $el
        this.type = type
        this.raw = data
        this.options = Object.assign({}, Peity.defaults[this.type], options)
    }

    svgElement(...args) {
        return svgElement(...args)
    }

    prepare(width, height) {
        if (!this.$svg) {
            this.$el.style.display = "none"
            this.$svg = svgElement("svg", {
                class: "peity"
            })
            this.$el.parentNode.insertBefore(this.$svg, this.$el)
        }
        this.$svg.innerHTML = ""
        this.$svg.setAttribute("width", width)
        this.$svg.setAttribute("height", height)
        return this.$svg
    }

    fill() {
        let f = this.options.fill
        return typeof f === "function"
            ? f
            : function (_, i) {
                  return f[i % f.length]
              }
    }

    draw() {
        Peity.graphers[this.type].call(this, this.options)
    }

    values() {
        return this.raw.split(this.options.delimiter).map(val => parseFloat(val))
    }
}

Peity.defaults = {}
Peity.graphers = {}

Peity.register = (type, factory) => {
    Peity.defaults[type] = factory.options
    Peity.graphers[type] = factory.draw
}

Peity.register("bar", bar)
Peity.register("donut", pie)
Peity.register("line", line)
Peity.register("pie", pie)

export default Peity
