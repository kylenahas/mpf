@tool
extends EditorPlugin
## Test-only: takes screenshots of the Godot editor for the MPF docs (docs-site/tools/editor_shots/take_shots.py).
##
## Started with the environment variable MPF_DOCS_EDITOR_SHOTS naming a JSON file, a list of shots. Each shot is either
##   {"scene": "res://x.tscn", "select": "Node/Path" or ".", "filter": optional text for the Inspector's filter box,
##    "screen": optional main screen ("2D"),  "crop": optional [x0, y0, x1, y1] as fractions, "width": optional px,
##    "out": "C:/path/file.png"}
## or {"create_dialog": true, "search": "MPFSlide", "out": ...} for the Create New Node dialog (put these last),
## or {"project_settings": "General"/"Plugins"/"Globals", "subtab": optional ("Autoload"), "search": optional text for
##     the General tab's filter, "section": optional section to click ("Run"), "out": ...} for the Project Settings
##     dialog.
## After the last shot the editor quits. Without the argument the plugin does nothing.

func _enter_tree() -> void:
	# An environment variable, not a command-line argument: Godot may restart the editor on a project's first open.
	var spec := OS.get_environment("MPF_DOCS_EDITOR_SHOTS")
	if spec and FileAccess.file_exists(spec):
		_run.call_deferred(spec)


func _run(spec_path: String) -> void:
	# let the editor finish starting and importing
	await get_tree().create_timer(4.0).timeout
	var shots: Array = JSON.parse_string(FileAccess.get_file_as_string(spec_path))
	for shot in shots:
		if shot.has("create_dialog"):
			await _create_dialog_shot(shot)
		elif shot.has("project_settings"):
			await _project_settings_shot(shot)
		else:
			await _scene_shot(shot)
		print("DOC_EDITOR_SHOT %s" % shot["out"])
	print("DOC_EDITOR_DONE")
	get_tree().quit()


func _scene_shot(shot: Dictionary) -> void:
	EditorInterface.open_scene_from_path(shot["scene"])
	await get_tree().create_timer(1.0).timeout
	EditorInterface.set_main_screen_editor(shot.get("screen", "2D"))
	var root := EditorInterface.get_edited_scene_root()
	var node: Node = root if shot["select"] == "." else root.get_node(shot["select"])
	var selection := EditorInterface.get_selection()
	selection.clear()
	selection.add_node(node)
	EditorInterface.edit_node(node)
	await get_tree().create_timer(0.5).timeout
	_set_inspector_filter(shot.get("filter", ""))
	if shot.has("tab"):
		# e.g. "GMC": bring a dock tab to the front
		_select_tab(EditorInterface.get_base_control(), shot["tab"])
	if shot.has("zoom"):
		for widget in EditorInterface.get_base_control().find_children("*", "EditorZoomWidget", true, false):
			if widget.is_visible_in_tree() and widget.has_method("set_zoom"):
				widget.set_zoom(float(shot["zoom"]))
				widget.emit_signal("zoom_changed", float(shot["zoom"]))
				print("DOC_EDITOR zoom set")
	if shot.has("pan"):
		# canvas position for the 2D view's top-left corner, through the 2D editor's scrollbars
		for editor in EditorInterface.get_base_control().find_children("*", "CanvasItemEditor", true, false):
			for bar in editor.find_children("*", "ScrollBar", true, false):
				if bar is HScrollBar:
					bar.value = float(shot["pan"][0])
				elif bar is VScrollBar:
					bar.value = float(shot["pan"][1])
			print("DOC_EDITOR pan set")
	await get_tree().create_timer(float(shot.get("wait", 1.0))).timeout
	# The editor only redraws on changes, so a frame may never come on its own: draw one now.
	_scrub_paths()
	RenderingServer.force_draw(false)
	_save(EditorInterface.get_base_control().get_viewport().get_texture().get_image(), shot)


func _create_dialog_shot(shot: Dictionary) -> void:
	EditorInterface.popup_create_dialog(func(_type): pass, "Node", "", "Create New Node")
	await get_tree().create_timer(1.0).timeout
	var dialog: Window = null
	for w in EditorInterface.get_base_control().find_children("*", "Window", true, false):
		if w.visible and w.get_class() == "CreateDialog":
			dialog = w
	if dialog == null:
		push_error("DOC_EDITOR no create dialog")
		return
	if shot.has("search"):
		for edit in dialog.find_children("*", "LineEdit", true, false):
			if edit.is_visible_in_tree():
				edit.text = shot["search"]
				edit.text_changed.emit(edit.text)
				break
	# Opened from code the dialog's button reads "Change"; from the Add Child Node button it reads "Create".
	dialog.get_ok_button().text = "Create"
	await get_tree().create_timer(float(shot.get("wait", 1.0))).timeout
	# The editor only redraws on changes, so a frame may never come on its own: draw one now.
	_scrub_paths()
	RenderingServer.force_draw(false)
	_save(dialog.get_texture().get_image(), shot)
	dialog.get_cancel_button().pressed.emit()
	await get_tree().create_timer(0.5).timeout


## Replace the test project's real folder in any visible text field (it's a temp folder under the user's name).
func _scrub_paths() -> void:
	var real := ProjectSettings.globalize_path("res://").trim_suffix("/")
	var real_back := real.replace("/", "\\")
	var fields := EditorInterface.get_base_control().find_children("*", "LineEdit", true, false)
	fields.append_array(EditorInterface.get_base_control().find_children("*", "TextEdit", true, false))
	for edit in fields:
		if not is_instance_valid(edit):
			continue
		for value in [real, real_back]:
			if value in edit.text:
				edit.text = edit.text.replace(value, "C:/pinball/my_machine")
			if value in edit.placeholder_text:
				edit.placeholder_text = edit.placeholder_text.replace(value, "C:/pinball/my_machine")


func _save(img: Image, shot: Dictionary) -> void:
	if shot.has("crop"):
		var c: Array = shot["crop"]
		var w := img.get_width()
		var h := img.get_height()
		img = img.get_region(Rect2i(int(c[0] * w), int(c[1] * h), int((c[2] - c[0]) * w), int((c[3] - c[1]) * h)))
	if shot.has("width") and img.get_width() > int(shot["width"]):
		var width := int(shot["width"])
		img.resize(width, int(img.get_height() * float(width) / img.get_width()), Image.INTERPOLATE_LANCZOS)
	img.save_png(shot["out"])


func _set_inspector_filter(text: String) -> void:
	for edit in EditorInterface.get_base_control().find_children("*", "LineEdit", true, false):
		if is_instance_valid(edit) and edit.placeholder_text == "Filter Properties" and edit.is_visible_in_tree():
			edit.text = text
			edit.text_changed.emit(text)


func _project_settings_shot(shot: Dictionary) -> void:
	var dialog: Window = null
	for w in EditorInterface.get_base_control().find_children("*", "ProjectSettingsEditor", true, false):
		dialog = w
	if dialog == null:
		push_error("DOC_EDITOR no project settings dialog")
		return
	# Open it the way the Project menu does, so Godot fills in the autoloads and plugins.
	var opened := false
	for menu in EditorInterface.get_base_control().find_children("*", "PopupMenu", true, false):
		for i in menu.item_count:
			if menu.get_item_text(i).begins_with("Project Settings"):
				menu.id_pressed.emit(menu.get_item_id(i))
				opened = true
				break
		if opened:
			break
	if not opened:
		dialog.popup_centered(Vector2i(1000, 640))
	await get_tree().create_timer(1.0).timeout
	dialog.size = Vector2i(1000, 640)
	await get_tree().create_timer(0.3).timeout
	_select_tab(dialog, shot["project_settings"])
	if shot.has("subtab"):
		_select_tab(dialog, shot["subtab"])
	if shot.has("search"):
		for edit in dialog.find_children("*", "LineEdit", true, false):
			if edit.is_visible_in_tree() and edit.placeholder_text.begins_with("Filter"):
				edit.text = shot["search"]
				edit.text_changed.emit(edit.text)
				break
	if shot.has("section"):
		await get_tree().create_timer(0.5).timeout
		for tree in dialog.find_children("*", "Tree", true, false):
			if tree.is_visible_in_tree() and tree.get_root():
				var item := _find_item(tree.get_root(), shot["section"])
				if item:
					tree.set_selected(item, 0)
					tree.item_selected.emit()
					break
	# The test-only screenshot plugin is enabled in the test project; leave it out of the Plugins list.
	for tree in dialog.find_children("*", "Tree", true, false):
		var root: TreeItem = tree.get_root()
		if root:
			for item in root.get_children():
				for column in tree.columns:
					if item.get_text(column).contains("Doc editor shots"):
						item.free()
						break
	await get_tree().create_timer(float(shot.get("wait", 1.0))).timeout
	_scrub_paths()
	RenderingServer.force_draw(false)
	_save(dialog.get_texture().get_image(), shot)
	dialog.hide()
	await get_tree().create_timer(0.5).timeout


func _select_tab(root: Node, title: String) -> void:
	for tabs in root.find_children("*", "TabContainer", true, false):
		if not tabs.is_visible_in_tree():
			continue
		for i in tabs.get_tab_count():
			if tabs.get_tab_title(i) == title:
				tabs.current_tab = i
				return


func _find_item(item: TreeItem, text: String) -> TreeItem:
	if item.get_text(0) == text:
		return item
	for child in item.get_children():
		var found := _find_item(child, text)
		if found:
			return found
	return null
