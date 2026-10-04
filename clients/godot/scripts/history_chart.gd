extends Control
## Read-only plotting of recorded history; no simulation calculations.

var history: Array = []
var metric := "gdp"
var colors: Dictionary = {}


func _ready() -> void:
	custom_minimum_size.y = 300
	resized.connect(queue_redraw)
	mouse_filter = Control.MOUSE_FILTER_PASS


func _draw() -> void:
	if history.is_empty():
		return
	var font := get_theme_default_font()
	var font_size := get_theme_default_font_size()
	var plot := Rect2(85, 20, maxf(100, size.x - 115), size.y - 70)
	var low := 0.0
	var high := 1.0
	for item in history:
		for faction in colors:
			var value := float(item.nations[faction].get(metric, 0))
			low = minf(low, value)
			high = maxf(high, value)
	for index in range(5):
		var fraction := float(index) / 4.0
		var y := plot.end.y - fraction * plot.size.y
		draw_line(Vector2(plot.position.x, y), Vector2(plot.end.x, y), Color("334350"))
		draw_string(font, Vector2(0, y + 5), "%.1f" % lerpf(low, high, fraction), HORIZONTAL_ALIGNMENT_LEFT, 80, font_size)
	for faction in colors:
		var points := PackedVector2Array()
		for index in range(history.size()):
			var value := float(history[index].nations[faction].get(metric, 0))
			points.append(Vector2(plot.position.x + plot.size.x * index / maxi(1, history.size() - 1), plot.end.y - (value - low) / (high - low) * plot.size.y))
		var color := Color(str(colors[faction]))
		if points.size() > 1:
			draw_polyline(points, color, 2.5, true)
		for point in points:
			draw_circle(point, 3, color)
	draw_string(font, Vector2(plot.position.x, size.y - 10), str(int(history[0].year)), HORIZONTAL_ALIGNMENT_LEFT, -1, font_size)
	if history.size() > 1:
		draw_string(font, Vector2(plot.end.x - 50, size.y - 10), str(int(history[-1].year)), HORIZONTAL_ALIGNMENT_LEFT, -1, font_size)
