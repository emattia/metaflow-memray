import json

def create_stats_histogram_html(histogram_data, width=600, height=600):
    # Designed to work with memray's stats data only.
    vega_data = []
    for item in histogram_data:
        try:
            vega_data.append({
                "bin_center": (float(item['min_bytes']) + float(item['max_bytes'])) / 2,
                "count": int(item['count']),
                "min_bytes": float(item['min_bytes']),
                "max_bytes": float(item['max_bytes'])
            })
        except (ValueError, KeyError) as e:
            print(f"Skipping invalid data point: {item}. Error: {e}")

    vega_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": vega_data},
        "vconcat": [
            {
                "width": width,
                "height": height * 0.25,
                "params": [
                    {
                        "name": "brush",
                        "select": {"type": "interval", "encodings": ["x"]}
                    }
                ],
                "mark": "bar",
                "encoding": {
                    "x": {
                        "field": "bin_center",
                        "type": "quantitative",
                        "scale": {"type": "log"},
                        "axis": {"title": "Byte Range (log scale)", "labelAngle": -45}
                    },
                    "y": {
                        "field": "count",
                        "type": "quantitative",
                        "axis": {"title": "Count"}
                    },
                    "tooltip": [
                        {"field": "min_bytes", "type": "quantitative", "title": "Min Bytes"},
                        {"field": "max_bytes", "type": "quantitative", "title": "Max Bytes"},
                        {"field": "count", "type": "quantitative", "title": "Count"}
                    ]
                },
                "title": "Overview: Histogram of Byte Ranges"
            },
            {
                "width": width,
                "height": height * 0.7,
                "transform": [
                    {"filter": {"param": "brush"}}
                ],
                "mark": "bar",
                "encoding": {
                    "x": {
                        "field": "bin_center",
                        "type": "quantitative",
                        "scale": {"type": "log", "domain": {"param": "brush"}},
                        "axis": {
                            "title": "Byte Range (log scale)",
                            "labelAngle": -60,
                            "labelFormat": "~s"
                        }
                    },
                    "y": {
                        "field": "count",
                        "type": "quantitative",
                        "axis": {"title": "Count"},
                        "scale": {"zero": False}
                    },
                    "tooltip": [
                        {"field": "min_bytes", "type": "quantitative", "title": "Min Bytes"},
                        {"field": "max_bytes", "type": "quantitative", "title": "Max Bytes"},
                        {"field": "count", "type": "quantitative", "title": "Count"}
                    ]
                },
                "title": "Detail: Selected Byte Range"
            }
        ],
        "config": {
            "view": {"stroke": None},
            "axis": {"domain": False},
            "axisX": {"labelPadding": 10}
        }
    }
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Byte Range Histogram</title>
        <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            #vis {{ width: 100%; height: {height}px; }}
        </style>
    </head>
    <body>
        <div id="vis"></div>
        <script type="text/javascript">
            var spec = {json.dumps(vega_spec)};
            vegaEmbed('#vis', spec);
        </script>
    </body>
    </html>
    """

    return html_template