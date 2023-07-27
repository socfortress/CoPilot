export default {
    options: {
        fill: ["#ff9900", "#fff4dd", "#ffc66e"],
        radius: 8
    },

    draw(opts) {
        if (!opts.delimiter) {
            var delimiter = this.raw.match(/[^0-9\.]/)
            opts.delimiter = delimiter ? delimiter[0] : ","
        }
        var values = this.values().map(n => (n > 0 ? n : 0))

        if (opts.delimiter === "/") {
            var v1 = values[0]
            var v2 = values[1]
            values = [v1, Math.max(0, v2 - v1)]
        }

        var i = 0
        var length = values.length
        var sum = 0

        for (; i < length; i++) {
            sum += values[i]
        }

        if (!sum) {
            length = 2
            sum = 1
            values = [0, 1]
        }

        var diameter = opts.radius * 2

        var $svg = this.prepare(opts.width || diameter, opts.height || diameter)

        var rect = $svg.getBoundingClientRect()
        var width = rect.width
        var height = rect.height
        var cx = width / 2
        var cy = height / 2

        var radius = Math.min(cx, cy)
        var innerRadius = opts.innerRadius

        if (this.type === "donut" && !innerRadius) {
            innerRadius = radius * 0.5
        }

        var pi = Math.PI
        var fill = this.fill()

        var scale = (this.scale = (value, radius) => {
            var radians = (value / sum) * pi * 2 - pi / 2

            return [radius * Math.cos(radians) + cx, radius * Math.sin(radians) + cy]
        })

        var cumulative = 0

        for (i = 0; i < length; i++) {
            var value = values[i]
            var portion = value / sum
            var $node

            if (portion === 0) continue

            if (portion === 1) {
                if (innerRadius) {
                    var x2 = cx - 0.01
                    var y1 = cy - radius
                    var y2 = cy - innerRadius

                    $node = this.svgElement("path", {
                        d: [
                            "M",
                            cx,
                            y1,
                            "A",
                            radius,
                            radius,
                            0,
                            1,
                            1,
                            x2,
                            y1,
                            "L",
                            x2,
                            y2,
                            "A",
                            innerRadius,
                            innerRadius,
                            0,
                            1,
                            0,
                            cx,
                            y2
                        ].join(" ")
                    })
                } else {
                    $node = this.svgElement("circle", {
                        cx: cx,
                        cy: cy,
                        r: radius
                    })
                }
            } else {
                var cumulativePlusValue = cumulative + value

                var d = ["M"].concat(
                    scale(cumulative, radius),
                    "A",
                    radius,
                    radius,
                    0,
                    portion > 0.5 ? 1 : 0,
                    1,
                    scale(cumulativePlusValue, radius),
                    "L"
                )

                if (innerRadius) {
                    d = d.concat(
                        scale(cumulativePlusValue, innerRadius),
                        "A",
                        innerRadius,
                        innerRadius,
                        0,
                        portion > 0.5 ? 1 : 0,
                        0,
                        scale(cumulative, innerRadius)
                    )
                } else {
                    d.push(cx, cy)
                }

                cumulative += value

                $node = this.svgElement("path", {
                    d: d.join(" ")
                })
            }

            $node.setAttribute("fill", fill.call(this, value, i, values))

            $svg.appendChild($node)
        }
    }
}
