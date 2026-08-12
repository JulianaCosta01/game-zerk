import pygame
import os
import sys
 
# Copy your config values here directly to test in isolation
PASTA_BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_ASSETS  = os.path.join(PASTA_BASE, "assets")
PASTA_SONS    = os.path.join(PASTA_ASSETS, "sounds")
PASTA_MUSICAS = os.path.join(PASTA_ASSETS, "music")
 
print("=== PATHS ===")
print(f"PASTA_BASE:    {PASTA_BASE}")
print(f"PASTA_ASSETS:  {PASTA_ASSETS}")
print(f"PASTA_SONS:    {PASTA_SONS}")
print(f"PASTA_MUSICAS: {PASTA_MUSICAS}")
 
print("\n=== FOLDER EXISTS? ===")
print(f"assets/       exists: {os.path.exists(PASTA_ASSETS)}")
print(f"sounds/       exists: {os.path.exists(PASTA_SONS)}")
print(f"music/        exists: {os.path.exists(PASTA_MUSICAS)}")
 
print("\n=== FILES IN sounds/ ===")
if os.path.exists(PASTA_SONS):
    print(os.listdir(PASTA_SONS))
else:
    print("FOLDER NOT FOUND")
 
print("\n=== FILES IN music/ ===")
if os.path.exists(PASTA_MUSICAS):
    print(os.listdir(PASTA_MUSICAS))
else:
    print("FOLDER NOT FOUND")
 
print("\n=== MUSIC FILE ===")
caminho_musica = os.path.join(PASTA_MUSICAS, "musica_fundo.ogg")
print(f"Full path: {caminho_musica}")
print(f"Exists:    {os.path.exists(caminho_musica)}")
 
print("\n=== SOUND FILES ===")
nomes_sons = ["tiro.wav", "explosao.wav", "coleta.wav",
              "zona_alerta.wav", "vitoria.wav", "derrota.wav"]
for arquivo in nomes_sons:
    caminho = os.path.join(PASTA_SONS, arquivo)
    print(f"{arquivo}: {'✅ found' if os.path.exists(caminho) else '❌ NOT FOUND'} — {caminho}")
 
print("\n=== PYGAME MIXER TEST ===")
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
print(f"Mixer initialized: {pygame.mixer.get_init()}")
 
if os.path.exists(caminho_musica):
    try:
        pygame.mixer.music.load(caminho_musica)
        pygame.mixer.music.play()
        print("Music loaded and playing — you should hear it for 3 seconds")
        pygame.time.wait(3000)
    except Exception as e:
        print(f"❌ Music error: {e}")
else:
    print("❌ Music file not found — cannot test playback")
 
pygame.quit()
