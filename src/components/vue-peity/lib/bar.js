export default {
    options: {
        delimiter: ",",
        fill: ["#4D89F9"],
        height: 16,
        min: 0,
        padding: 0.1,
        width: 32
    },

    draw(opts) {
        var values = this.values()
        var max = Math.max.apply(Math, opts.max === undefined ? values : values.concat(opts.max))
        var min = Math.min.apply(Math, opts.min === undefined ? values : values.concat(opts.min))

        var $svg = this.prepare(opts.width, opts.height)
        var rect = $svg.getBoundingClientRect()

        var width = rect.width
        var height = rect.height
        var diff = max - min
        var padding = opts.padding
        var fill = this.fill()

        var xScale = (this.x = input => {
            return (input * width) / values.length
        })

        var yScale = (this.y = input => {
            return height - (diff ? ((input - min) / diff) * height : 1)
        })

        for (var i = 0; i < values.length; i++) {
            var x = xScale(i + padding)
            var w = xScale(i + 1 - padding) - x
            var value = values[i]
            var valueY = yScale(value)
            var y1 = valueY
            var y2 = valueY
            var h

            if (!diff) {
                h = 1
            } else if (value < 0) {
                y1 = yScale(Math.min(max, 0))
            } else {
                y2 = yScale(Math.max(min, 0))
            }

            h = y2 - y1

            if (h === 0) {
                h = 1
                if (max > 0 && diff) y1--
            }

            $svg.appendChild(
                this.svgElement("rect", {
                    fill: fill.call(this, value, i, values),
                    x: x,
                    y: y1,
                    width: w,
                    height: h
                })
            )
        }
    }
}
