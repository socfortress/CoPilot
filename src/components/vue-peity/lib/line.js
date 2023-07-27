export default {
    options: {
        delimiter: ",",
        fill: "#c6d9fd",
        height: 16,
        min: 0,
        stroke: "#4d89f9",
        strokeWidth: 1,
        width: 32
    },

    draw(opts) {
        var values = this.values()
        if (values.length === 1) values.push(values[0])
        var max = Math.max.apply(Math, opts.max === undefined ? values : values.concat(opts.max))
        var min = Math.min.apply(Math, opts.min === undefined ? values : values.concat(opts.min))

        var $svg = this.prepare(opts.width, opts.height)
        var rect = $svg.getBoundingClientRect()
        var strokeWidth = opts.strokeWidth
        var width = rect.width
        var height = rect.height - strokeWidth
        var diff = max - min

        var xScale = (this.x = input => {
            return input * (width / (values.length - 1))
        })

        var yScale = (this.y = input => {
            var y = height

            if (diff) {
                y -= ((input - min) / diff) * height
            }

            return y + strokeWidth / 2
        })

        var zero = yScale(Math.max(min, 0))
        var coords = [0, zero]

        for (var i = 0; i < values.length; i++) {
            coords.push(xScale(i), yScale(values[i]))
        }

        coords.push(width, zero)

        if (opts.fill) {
            $svg.appendChild(
                this.svgElement("polygon", {
                    fill: opts.fill,
                    points: coords.join(" ")
                })
            )
        }

        if (strokeWidth) {
            $svg.appendChild(
                this.svgElement("polyline", {
                    fill: "none",
                    points: coords.slice(2, coords.length - 2).join(" "),
                    stroke: opts.stroke,
                    "stroke-width": strokeWidth,
                    "stroke-linecap": "square"
                })
            )
        }
    }
}
