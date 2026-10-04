extends Node
## Short local synthesized cues, silent until enabled.

var player: AudioStreamPlayer


func _ready() -> void:
	player = AudioStreamPlayer.new()
	add_child(player)


func cue(event: String, preferences: Dictionary) -> void:
	if not preferences.get("sound_enabled", false) or int(preferences.get("sound_volume", 0)) == 0:
		return
	var notes: Array = {"order": [520.0], "warning": [240.0, 190.0], "commit": [440.0, 550.0], "resolve": [440.0, 660.0, 880.0], "victory": [523.25, 659.25, 783.99, 1046.5]}.get(event, [520.0])
	var rate := 22050
	var samples := PackedByteArray()
	for frequency in notes:
		var count := int(rate * 0.09)
		for index in range(count):
			var envelope := sin(PI * float(index) / count)
			var sample := int(sin(TAU * float(frequency) * index / rate) * envelope * 7000)
			samples.append(sample & 255)
			samples.append((sample >> 8) & 255)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.data = samples
	player.stream = stream
	player.volume_db = linear_to_db(float(preferences.sound_volume) / 100.0)
	player.play()
