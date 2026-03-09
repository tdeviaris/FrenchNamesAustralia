# Conversion WAV → MP3 (ffmpeg)

Commande (mono, 44.1 kHz, 128 kbps) :

```bash
ffmpeg -i input.wav -ac 1 -ar 44100 -codec:a libmp3lame -b:a 128k output.mp3
```

Notes :
- `-ac 1` : sortie en mono
- `-ar 44100` : fréquence d’échantillonnage 44,1 kHz
- `-b:a 128k` : bitrate audio 128 kbps

