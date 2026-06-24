import sys
from vosk import Model, KaldiRecognizer
model = Model('model')
rec = KaldiRecognizer(model, 16000, '["hey jarvis", "jarvis", "[unk]"]')
print('OK')
