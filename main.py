import os
import sys
import asyncio
import pygame
import audio

from config import LARGURA_TELA, ALTURA_TELA, FPS, TITULO, PASTA_SONS, PASTA_MUSICAS
from menu import executar_menu
from game_state import EstadoJogo


def carregar_audio():
    """Carrega música e efeitos sonoros e retorna o dicionário de sons."""
    sons = {}
    # Música de fundo
    caminho_musica = os.path.join(PASTA_MUSICAS, "musica_fundo.ogg")
    if os.path.exists(caminho_musica):
        pygame.mixer.music.load(caminho_musica)
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(loops=-1)
           
    # Efeitos sonoros 
    nomes_sons = {
        "tiro":        "tiro.ogg",
        "explosao":    "explosao.ogg",
        "coleta":      "coleta.ogg",
        "zona_alerta": "zona_alerta.ogg",
        "vitoria":     "vitoria.ogg",
        "derrota":     "derrota.ogg",
    }

    for chave, arquivo in nomes_sons.items():
        caminho = os.path.join(PASTA_SONS, arquivo)
        if os.path.exists(caminho):
            try:
                sons[chave] = pygame.mixer.Sound(caminho)
                sons[chave].set_volume(0.6)
            except pygame.error:
                sons[chave] = None   # Falhou ao carregar (ignora)
        else:
            sons[chave] = None   # Arquivo não existe (sem efeito)

    return sons


def tocar_musica_fundo():
    """Toca a música de fundo em loop, se o mixer estiver disponível e ela não estiver tocando."""
    if pygame.mixer.get_init() and not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(loops=-1)


async def executar_jogo(tela):
    """
    Executa o loop principal do jogo.

    Cria um EstadoJogo novo e roda até o jogador fechar a janela
    ou pressionar ESC na tela inicial.

    Args:
        tela: pygame.Surface principal

    Returns:
        bool: True → voltar ao menu, False → encerrar o programa
    """
    relogio    = pygame.time.Clock()
    estado     = EstadoJogo()
    zona_ativa = False   # Controla quando tocar o alerta de zona
    fim_processado  = False
    estado_anterior = "inicio"

    tocar_musica_fundo()

    rodando = True
    while rodando:
        eventos = pygame.event.get()
        for evento in eventos:
            if evento.type == pygame.QUIT:
                return False   # Fechou a janela → encerra o programa

            if evento.type == pygame.KEYDOWN:
                # ESC na tela inicial → volta ao menu
                if evento.key == pygame.K_ESCAPE and estado.estado == "inicio":
                    return True

        teclas    = pygame.key.get_pressed()
        pos_mouse = pygame.mouse.get_pos()

        # dt limitado a 100ms para não dar salto grande após uma pausa
        dt = min(relogio.tick(FPS), 100)

        estado.atualizar(dt, teclas, pos_mouse, eventos)

        # Voltou a jogar depois da tela de fim: reseta os flags de áudio
        if estado_anterior == "fim" and estado.estado == "jogando":
            fim_processado = False
            zona_ativa     = False
            tocar_musica_fundo()

        estado_anterior = estado.estado

        # Áudio dinâmico baseado no estado do jogo
        if estado.estado == "jogando" and estado.zona.ativa:
            if not zona_ativa:
                zona_ativa = True
                # Toca o alerta só na primeira vez que a zona ativa
                if audio.sons.get("zona_alerta"):
                    audio.sons["zona_alerta"].play()

        if estado.estado == "fim" and not fim_processado:
            fim_processado = True
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()

            if estado.vitoria and audio.sons.get("vitoria"):
                audio.sons["vitoria"].play()
            elif not estado.vitoria and audio.sons.get("derrota"):
                audio.sons["derrota"].play()

            zona_ativa = False   # Reseta para a próxima partida

        tela.fill((5, 8, 16))   # Cor de fundo padrão (quase preto)
        estado.desenhar(tela)

        pygame.display.flip()

        # Cede o controle pro loop de eventos do navegador a cada frame.
        # Necessário pro pygbag (build web); no desktop é um no-op.
        await asyncio.sleep(0)

    return True


async def main():
    """
    Função principal — inicializa o Pygame e alterna entre menu e jogo.
    """

    pygame.init()

    # Inicializa o som separadamente: se a máquina não tiver dispositivo de
    # áudio disponível, o jogo continua rodando mudo em vez de travar.
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(16)
    except pygame.error as e:
        print(f"Aviso: não foi possível inicializar o áudio ({e}). Jogo vai rodar sem som.")

    # Configura o título da janela
    pygame.display.set_caption(TITULO)

    tela = pygame.display.set_mode(
        (LARGURA_TELA, ALTURA_TELA),
        pygame.HWSURFACE | pygame.DOUBLEBUF
    )

    # Carrega os recursos de áudio (se o mixer não iniciou, cada som fica None)
    audio.sons = carregar_audio() if pygame.mixer.get_init() else {}

    while True:
        deve_jogar = await executar_menu(tela)

        if not deve_jogar:
            break

        # Executa o jogo
        deve_continuar = await executar_jogo(tela)
        tocar_musica_fundo()

        if not deve_continuar:
            break

    pygame.quit()

    # No navegador (pygbag/emscripten) sys.exit() encerraria o runtime de
    # forma abrupta; no desktop, encerra o processo normalmente.
    if sys.platform != "emscripten":
        sys.exit()

if __name__ == "__main__":
    asyncio.run(main())
