
import sys
import pygame
import audio

from config import LARGURA_TELA, ALTURA_TELA, FPS, TITULO, PASTA_SONS, PASTA_MUSICAS
from menu          import executar_menu
from game_state   import EstadoJogo
import os

def carregar_audio():
    '''
    Carrega todos os recursos de áudio do jogo.
    '''
    sons = {}
    # Música de fundo
    caminho_musica = os.path.join(PASTA_MUSICAS, "musica_fundo.ogg")
    if os.path.exists(caminho_musica):
        pygame.mixer.music.load(caminho_musica)
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(loops=-1)
           
    # Efeitos sonoros 
    nomes_sons = {
        "tiro":        "tiro.wav",  
        "explosao":    "explosao.wav",
        "coleta":      "coleta.wav", 
        "zona_alerta": "zona_alerta.wav", 
        "vitoria":     "vitoria.wav",
        "derrota":     "derrota.wav", 
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

def executar_jogo(tela):
    """
    Executa o loop principal do jogo.

    Cria um EstadoJogo novo e roda até o jogador fechar a janela
    ou pressionar ESC na tela inicial.

    Args:
        tela: pygame.Surface principal
        sons: dicionário com sons carregados por carregar_audio()

    Returns:
        bool: True → voltar ao menu, False → encerrar o programa
    """
    relogio    = pygame.time.Clock()
    estado     = EstadoJogo()
    zona_ativa = False   # Controla quando tocar o alerta de zona
    fim_processado = False
    estado_anterior = "inicio"

    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(loops=-1)

    

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


        '''
        # Delta time: tempo real desde o último frame
            # clock.tick(FPS) aguarda o necessário para manter 60fps.
            # Limitamos dt a 100ms para evitar saltos após pausas.
        '''
        dt = min(relogio.tick(FPS), 100)

       
        # Atualizar toda a lógica do jogo
        estado.atualizar(dt, teclas, pos_mouse, eventos)

        if estado_anterior == "fim" and estado.estado == "jogando":
            fim_processado = False
            zona_ativa     = False
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(loops=-1)

        estado_anterior = estado.estado

      
        # Áudio dinâmico baseado no estado do jogo
        if estado.estado == "jogando" and estado.zona.ativa:
            if not zona_ativa:
                zona_ativa = True
                # Toca alerta quando a zona ativa pela primeira vez
                if audio.sons.get("zona_alerta"):
                    audio.sons["zona_alerta"].play()
        if estado.estado == "fim" and not fim_processado:
            fim_processado = True
            pygame.mixer.music.stop()

            
            if estado.vitoria and audio.sons.get("vitoria"):
                    audio.sons["vitoria"].play()
            elif not estado.vitoria and audio.sons.get("derrota"):
                    audio.sons["derrota"].play()
                
            zona_ativa = False   # Reseta para a próxima partida


        tela.fill((5, 8, 16))   # Cor de fundo padrão (quase preto)
        estado.desenhar(tela)

        pygame.display.flip()

    return True


def main():
    """
    Função principal — inicializa o Pygame e alterna entre menu e jogo.
    """

    pygame.init()

    # Inicializa o sistema de som separadamente
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(16)

    # Configura o título da janela
    pygame.display.set_caption(TITULO)

    tela = pygame.display.set_mode(
        (LARGURA_TELA, ALTURA_TELA),
        pygame.HWSURFACE | pygame.DOUBLEBUF
    )

    # Carrega todos os recursos de áudio
    audio.sons = carregar_audio()

    while True:
        deve_jogar = executar_menu(tela)

        if not deve_jogar:
            break   

        # Executa o jogo
        deve_continuar = executar_jogo(tela)
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(loops=-1)

        if not deve_continuar:
            break   
        

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
