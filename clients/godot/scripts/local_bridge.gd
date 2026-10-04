extends Node
## One supervised Python process. Blocking pipe IO runs off the UI thread.

signal replied(message: Dictionary)
signal failed(message: String)
signal busy_changed(value: bool)

const MUTATIONS = ["new", "load", "edit", "commit", "reopen", "undo", "reset", "remember", "restore", "recover", "ui"]
var revision: int = 0
var last_command: String = ""
var busy: bool = false
var pid: int = -1
var _pipe: FileAccess
var _stderr: FileAccess
var _thread: Thread
var _timeout: Timer
var _next_id: int = 0
var _closing: bool = false
var _request_id: String = ""


func start() -> bool:
	_timeout = Timer.new()
	_timeout.one_shot = true
	_timeout.wait_time = 30.0
	_timeout.timeout.connect(_timed_out)
	add_child(_timeout)
	var python := OS.get_environment("WW3_PYTHON")
	if python.is_empty():
		var relative := "../../.venv/Scripts/python.exe" if OS.get_name() == "Windows" else "../../.venv/bin/python"
		python = ProjectSettings.globalize_path("res://" + relative).simplify_path()
	if not FileAccess.file_exists(python):
		failed.emit("Python was not found. Follow the Godot setup in README.md or set WW3_PYTHON to the project interpreter.")
		return false
	var save_dir := OS.get_environment("WW3_GODOT_SAVE_DIR")
	if save_dir.is_empty():
		save_dir = ProjectSettings.globalize_path("user://recovery")
	var process := OS.execute_with_pipe(python, PackedStringArray(["-u", "-m", "ww3.bridge", "--save-dir", save_dir]), true)
	if process.is_empty():
		failed.emit("The game simulation could not start. Check the Python installation.")
		return false
	pid = int(process.pid)
	_pipe = process.stdio
	_stderr = process.stderr
	return true


func send(command: String, params: Dictionary = {}) -> bool:
	if busy or _closing or pid < 0:
		return false
	_next_id += 1
	_request_id = str(_next_id)
	last_command = command
	var request := {"protocol_version": 1, "id": _request_id, "command": command, "params": params}
	if command in MUTATIONS:
		request.expected_revision = revision
	busy = true
	busy_changed.emit(true)
	_timeout.start()
	_thread = Thread.new()
	# Preserve map insertion order and full floating-point precision. The save
	# payload itself stays an opaque string across the language boundary.
	var error := _thread.start(_exchange.bind(JSON.stringify(request, "", false, true)))
	if error != OK:
		_timeout.stop()
		busy = false
		busy_changed.emit(false)
		failed.emit("Could not start the game communication thread.")
		return false
	return true


func _exchange(payload: String) -> void:
	_pipe.store_buffer((payload + "\n").to_utf8_buffer())
	var line := _pipe.get_line()
	var message: Variant = JSON.parse_string(line)
	if not _closing:
		call_deferred("_finish", message)


func _finish(message: Variant) -> void:
	if _thread != null and _thread.is_started():
		_thread.wait_to_finish()
	_thread = null
	_timeout.stop()
	busy = false
	busy_changed.emit(false)
	if _closing:
		return
	if not message is Dictionary or message.get("id") != _request_id or int(message.get("protocol_version", 0)) != 1:
		failed.emit("The game simulation stopped responding. Restart the client to recover the latest checkpoint.")
		shutdown()
		return
	var incoming := int(message.get("revision", -1))
	if incoming < revision:
		failed.emit("An outdated response was ignored. Refresh the campaign before continuing.")
		return
	revision = incoming
	replied.emit(message)


func _timed_out() -> void:
	shutdown()
	failed.emit("The simulation timed out. Restart to recover the latest checkpoint.")


func shutdown() -> void:
	_closing = true
	if pid > 0 and OS.is_process_running(pid):
		OS.kill(pid)
	pid = -1
	if _thread != null and _thread.is_started():
		_thread.wait_to_finish()
	_thread = null
	if _pipe != null:
		_pipe.close()
		_pipe = null
	if _stderr != null:
		_stderr.close()
		_stderr = null
	busy = false


func _exit_tree() -> void:
	shutdown()
