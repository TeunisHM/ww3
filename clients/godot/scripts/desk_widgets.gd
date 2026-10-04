extends RefCounted
## Small native controls shared by the command screens.

static func text(parent: Node, value: String, size: int = 0) -> Label:
	var label := Label.new()
	label.text = value
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if size > 0:
		label.add_theme_font_size_override("font_size", size)
	parent.add_child(label)
	return label


static func prose(parent: Node, value: String) -> RichTextLabel:
	var label := RichTextLabel.new()
	label.text = value
	label.fit_content = true
	label.scroll_active = false
	label.selection_enabled = true
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(label)
	return label


static func button(parent: Node, caption: String, action: Callable) -> Button:
	var control := Button.new()
	control.text = caption
	control.custom_minimum_size.y = 34
	control.pressed.connect(action)
	parent.add_child(control)
	return control


static func row(parent: Node) -> HBoxContainer:
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	parent.add_child(box)
	return box


static func column(parent: Node) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 10)
	parent.add_child(box)
	return box


static func section(parent: Node, caption: String) -> VBoxContainer:
	var panel := PanelContainer.new()
	parent.add_child(panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 12)
	panel.add_child(margin)
	var box := column(margin)
	text(box, caption).modulate = Color("71d6bc")
	return box


static func spin(parent: Node, caption: String, value: float, maximum: float, step: float = 1.0, minimum: float = 0.0) -> SpinBox:
	var line := row(parent)
	text(line, caption)
	var control := SpinBox.new()
	control.min_value = minimum
	control.max_value = maxf(maximum, value)
	control.step = step
	control.value = value
	control.custom_minimum_size.x = 145
	line.add_child(control)
	return control


static func choice(parent: Node, caption: String, values: Array, selected: String) -> OptionButton:
	var line := row(parent)
	text(line, caption)
	var control := OptionButton.new()
	for value in values:
		control.add_item(str(value))
		if str(value) == selected:
			control.select(control.item_count - 1)
	line.add_child(control)
	return control


static func table(parent: Node, headings: Array, rows: Array) -> Tree:
	var tree := Tree.new()
	tree.columns = headings.size()
	tree.hide_root = true
	tree.column_titles_visible = true
	tree.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var font_size: int = parent.get_theme_default_font_size() if parent is Control else 16
	tree.custom_minimum_size.y = clampi((rows.size() + 1) * (font_size + 12) + 12, 80, 380)
	for index in range(headings.size()):
		tree.set_column_title(index, str(headings[index]))
		tree.set_column_expand(index, true)
		tree.set_column_custom_minimum_width(index, 150 if index == 0 else 100)
	parent.add_child(tree)
	var root := tree.create_item()
	for values in rows:
		var item := tree.create_item(root)
		for index in range(values.size()):
			item.set_text(index, str(values[index]))
			item.set_tooltip_text(index, str(values[index]))
	return tree


static func number(value: Variant, decimals: int = 2) -> String:
	if value == null:
		return "—"
	return ("%." + str(decimals) + "f") % float(value)


static func entries(parent: Node, data: Dictionary, heading: String = "Item") -> void:
	var rows: Array = []
	for key in data:
		rows.append([str(key).replace("_", " ").capitalize(), number(data[key], 4)])
	table(parent, [heading, "Value"], rows)


static func clear(parent: Node) -> void:
	for child in parent.get_children():
		parent.remove_child(child)
		child.queue_free()
