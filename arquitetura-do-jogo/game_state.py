# =============================================================================
# game_state.py: Coordenador Central do Jogo
# =============================================================================


import pygame
import math
import random
import json
import os
from config import (
    POSICOES_INIMIGOS, POSICOES_ITENS,
    VELOCIDADE_INIMIGO_BASE, VELOCIDADE_INIMIGO_PASSO, VELOCIDADE_INIMIGO_MAX, INIMIGO_ALCANCE_BASE, INIMIGO_ALCANCE_PASSO, INIMIGO_ALCANCE_MAX,
    INIMIGO_AGRESSIVIDADE_BASE, INIMIGO_AGRESSIVIDADE_PASSO, INIMIGO_AGRESSIVIDADE_MAX,

    PONTOS_POR_KILL, JANELA_COMBO_MS,
    COR_INIMIGO, COR_BRILHO_INIMIGO,
    
    LARGURA_TELA, ALTURA_TELA
)
from tilemap       import Labirinto
from door      import PortaAutomatica
from player    import Jogador, Projetil
from enemy    import Inimigo
from zone       import ZonaVermelha, Particula, ItemEspecial
from zone       import criar_explosao, criar_coleta_item
from hud        import HUD, desenhar_tela_inicial, desenhar_tela_fim

# Arquivo onde o recorde é salvo localmente
ARQUIVO_SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.json")


def carregar_recorde():
    """
    Lê o recorde salvo em disco.
    Retorna 0 se o arquivo não existir ou estiver corrompido.
    """
    try:
        with open(ARQUIVO_SAVE, "r") as f:
            return json.load(f).get("recorde", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def salvar_recorde(pontuacao):
    """
    Salva o recorde se a pontuação atual for maior que o anterior.

    Args:
        pontuacao (int): pontuação a verificar e possivelmente salvar
    """
    if pontuacao > carregar_recorde():
        with open(ARQUIVO_SAVE, "w") as f:
            json.dump({"recorde": pontuacao}, f)


class EstadoJogo:
    """
    Concentra todo o estado e lógica da partida.

    ESTADOS POSSÍVEIS (self.estado):
        "inicio"   → tela inicial aguardando ENTER
        "jogando"  → partida em andamento
        "fim"      → partida encerrada (vitória ou derrota)
    """

    def __init__(self):
        self.numero_sessao = 0                    # Conta quantas partidas foram jogadas
        self.recorde       = carregar_recorde()   # Melhor pontuação já registrada
        self.estado        = "inicio"            # Estado inicial: tela de espera

        # Subsistemas do jogo (criados/recriados a cada nova partida)
        self.labirinto  = Labirinto()   # Mapa fixo — criado uma vez só
        self.hud        = HUD()         # Interface — criada uma vez só
        self.jogador    = None          # Criado em nova_partida()
        self.inimigos   = []
        self.projeteis  = []
        self.particulas = []
        self.itens      = []
        self.zona       = None

        '''
        # Portas automáticas do laboratório — fixas no mapa, criadas uma
        # única vez. Coordenadas (coluna, linha) e orientação conforme o
        # LAYOUT_MAPA ('D' nas posições linha=8,col=10 e linha=11,col=9).
        '''
        self.portas = [
    PortaAutomatica(coluna=8,  linha=8,  orientacao="vertical"),
    PortaAutomatica(coluna=9,  linha=11, orientacao="horizontal"),
]
        # Dados da partida atual
        self.pontuacao      = 0
        self.combo          = 1
        self.ms_ultimo_kill = 0     # Timestamp do último inimigo eliminado
        self.total_inimigos = 0
        self.vitoria        = False
        self.ms_inicio      = 0     # Timestamp de início da partida
        self.ms_fim         = 0     # Snapshot de ms_decorridos ao encerrar a partida

    
    # NOVA PARTIDA
    def nova_partida(self):
        """
        Reinicia todos os sistemas para uma nova partida.

        DIFICULDADE PROGRESSIVA:
        A cada sessão a velocidade dos inimigos aumenta em VELOCIDADE_INIMIGO_PASSO,
        até o máximo de VELOCIDADE_INIMIGO_MAX. Isso torna cada partida
        progressivamente mais desafiadora.
        """
        self.numero_sessao += 1

        # Calcula velocidade dos inimigos desta sessão
        vel_inimigos = min(
            VELOCIDADE_INIMIGO_BASE + (self.numero_sessao - 1) * VELOCIDADE_INIMIGO_PASSO,
            VELOCIDADE_INIMIGO_MAX
        )

        alcance = min(
            INIMIGO_ALCANCE_BASE + (self.numero_sessao -1 ) * INIMIGO_ALCANCE_PASSO, INIMIGO_ALCANCE_MAX
        )



        # Reinicia dados da partida
        self.pontuacao      = 0
        self.combo          = 1
        self.ms_ultimo_kill = 0
        self.vitoria        = False

        # Jogador começa no canto superior esquerdo (tile 1,1)
        self.jogador = Jogador(coluna_inicio=1, linha_inicio=1)

        # Cria todos os inimigos nas posições definidas em config.py
        self.inimigos = [
            Inimigo(coluna=c, linha=l, velocidade=vel_inimigos, alcance = alcance)
            for (l, c) in POSICOES_INIMIGOS
        ]
        self.total_inimigos = len(self.inimigos)

        # Reinicia listas de objetos dinâmicos
        self.projeteis  = []
        self.particulas = []

        # Cria os itens especiais nas posições definidas
        self.itens = [
            ItemEspecial(coluna=c, linha=l, tipo=t)
            for (l, c, t) in POSICOES_ITENS
        ]

        # Cria a zona vermelha (começa inativa)
        self.zona = ZonaVermelha()

        # Reinicia as portas automáticas (começam fechadas)
        for porta in self.portas:
            porta.abertura = 0.0

        # Marca o timestamp de início
        self.ms_inicio = pygame.time.get_ticks()

        self.estado = "jogando"

   
    # PROPRIEDADES DE TEMPO
    @property
    def ms_decorridos(self):
        """Milissegundos desde o início da partida."""
        return pygame.time.get_ticks() - self.ms_inicio

    @property
    def segundos_decorridos(self):
        """Segundos desde o início da partida (como float)."""
        # Quando a partida já terminou, o cronômetro fica parado no valor
        # registrado em _finalizar(), em vez de continuar contando.
        if self.estado == "fim":
            return self.ms_fim / 1000.0
        return self.ms_decorridos / 1000.0

    
    # ATUALIZAÇÃO: chamado uma vez por frame
    def atualizar(self, dt, teclas, pos_mouse, eventos):
        """
        Atualiza toda a lógica do jogo a cada frame.

        SEQUÊNCIA DE ATUALIZAÇÃO POR FRAME:
          1. Processa eventos de teclado (Enter, ESC)
          2. Atualiza o jogador (movimento, mira, disparo)
          3. Atualiza inimigos (IA, movimento)
          4. Move todos os projéteis
          5. Verifica colisões projétil → inimigo
          6. Verifica colisão jogador → inimigo
          7. Verifica colisão jogador → zona vermelha
          8. Verifica coleta de itens especiais
          9. Atualiza partículas e itens (animação)
          10. Atualiza a zona vermelha
          11. Verifica condição de vitória

        Args:
            dt        (float): delta time em ms
            teclas    : pygame.key.get_pressed()
            pos_mouse : (x, y) do cursor do mouse
            eventos   : lista de pygame.event da fila
        """
        # Eventos de teclado
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    if self.estado in ("inicio", "fim"):
                        self.nova_partida()
                if evento.key == pygame.K_ESCAPE:
                    if self.estado == "fim":
                        self.estado = "inicio"

        if self.estado != "jogando":
            return  

        # Jogador 
        self.jogador.atualizar(teclas, pos_mouse, dt, self.projeteis, self.labirinto)

        # Inimigos 
        inimigos_vivos = sum(1 for e in self.inimigos if e.vivo)
        congelado      = self.jogador.powerups["congelar"] > 0

        for inimigo in self.inimigos:
            inimigo.atualizar(dt, self.zona.margem, congelado, self.labirinto)

        # Projéteis 
        for proj in self.projeteis:
            proj.atualizar()
        self.projeteis = [p for p in self.projeteis if p.ativo]

        # Colisão projétil → inimigo 
        self._checar_colisoes_projetil_inimigo()

        # Colisão jogador → inimigo (sem escudo)
        if not self.jogador.tem_escudo:
            self._checar_colisao_jogador_inimigo()

        # Colisão jogador → zona vermelha 
        if self.jogador.vivo:
            self._checar_colisao_jogador_zona()

        # Coleta de itens especiais
        self._checar_coleta_itens()

        # Itens e partículas (animação) 
        for item in self.itens:
            item.atualizar(dt)
        for p in self.particulas:
            p.atualizar(dt)
        self.particulas = [p for p in self.particulas if not p.morta]

        # Portas automáticas
        # Abrem quando o jogador ou algum inimigo vivo está próximo.
        posicoes_entidades = [(self.jogador.x, self.jogador.y)]
        for inimigo in self.inimigos:
            if inimigo.vivo:
                posicoes_entidades.append((inimigo.x, inimigo.y))
        for porta in self.portas:
            porta.atualizar(posicoes_entidades)

        # Zona vermelha
        self.zona.atualizar(dt, self.segundos_decorridos, inimigos_vivos, congelado)

        # Condição de vitória 
        if all(not e.vivo for e in self.inimigos) and self.jogador.vivo:
            self._acionar_vitoria()

   
    # VERIFICAÇÕES DE COLISÃO
    def _checar_colisoes_projetil_inimigo(self):
        """
        Verifica colisão entre todos os projéteis e todos os inimigos.

        ALGORITMO O(n × m): para cada projétil, verifica contra cada inimigo.
        Suficientemente eficiente para o tamanho deste jogo.

        Ao acertar:
          - Projétil e inimigo são desativados
          - Incrementa contadores de hit e pontuação
          - Atualiza o combo
          - Gera partículas de explosão
        """
        for proj in self.projeteis:
            if not proj.ativo:
                continue
            for inimigo in self.inimigos:
                if not inimigo.vivo:
                    continue
                if inimigo.colide_com_projetil(proj.x, proj.y):
                    # Projétil acertou!
                    proj.ativo = False
                    inimigo.acertar()
                    self.jogador.acertos += 1

                    # Atualiza combo: kills consecutivos dentro de JANELA_COMBO_MS
                    agora = pygame.time.get_ticks()
                    if agora - self.ms_ultimo_kill < JANELA_COMBO_MS:
                        self.combo = min(self.combo + 1, 10)
                    else:
                        self.combo = 1
                    self.ms_ultimo_kill = agora

                    # Pontuação com multiplicador de combo
                    self.pontuacao += PONTOS_POR_KILL * self.combo

                    # Cria explosão de partículas no local do inimigo
                    self.particulas.extend(
                        criar_explosao(inimigo.x, inimigo.y,
                                       COR_INIMIGO, COR_BRILHO_INIMIGO)
                    )
                    break   # Um projétil acerta apenas um inimigo

    def _checar_colisao_jogador_inimigo(self):
        """
        Verifica se o jogador tocou algum inimigo vivo.
        Sem escudo → game over imediato.
        """
        if not self.jogador.vivo:
            return
        for inimigo in self.inimigos:
            if not inimigo.vivo:
                continue
            if inimigo.colide_com_jogador(
                    self.jogador.x, self.jogador.y, self.jogador.tamanho):
                self._acionar_derrota("impostor")
                return

    def _checar_colisao_jogador_zona(self):
        """Verifica se o jogador entrou na zona vermelha → game over."""
        if not self.jogador.vivo:
            return
        if self.zona.jogador_na_zona(
                self.jogador.x, self.jogador.y, self.jogador.tamanho):
            self._acionar_derrota("zona")

    def _checar_coleta_itens(self):
        """Verifica se o jogador coletou algum item especial."""
        for item in self.itens:
            if not item.ativo:
                continue
            if item.verificar_coleta(
                    self.jogador.x, self.jogador.y, self.jogador.tamanho):
                # Ativa o power-up correspondente no jogador
                self.jogador.ativar_powerup(item.tipo)
                # Cria partículas de coleta
                self.particulas.extend(
                    criar_coleta_item(item.x, item.y, item.meta["cor"])
                )

 
    # FIM DE PARTIDA
    def _acionar_derrota(self, motivo=""):
        """Encerra a partida por derrota."""
        self.jogador.vivo = False
        self.vitoria      = False
        self._finalizar()

    def _acionar_vitoria(self):
        """
        Encerra a partida por vitória.
        Adiciona bônus de tempo: completar mais rápido = mais pontos.
        """
        self.vitoria = True

        # Bônus de tempo: 10 pontos por segundo abaixo do tempo esperado (120s)
        tempo_esperado = 120.0
        tempo_restante = max(0, tempo_esperado - self.segundos_decorridos)
        self.pontuacao += int(tempo_restante * 10)

        self._finalizar()

    def _finalizar(self):
        """Procedimentos comuns ao encerrar (vitória ou derrota)."""
        self.ms_fim  = self.ms_decorridos  # Congela o cronômetro no tempo final
        salvar_recorde(self.pontuacao)
        self.recorde = carregar_recorde()
        self.combo   = 1
        self.estado  = "fim"

    
    # RENDERIZAÇÃO
    def desenhar(self, tela):
        """
        Renderiza todo o estado visual do jogo.

        ORDEM DE RENDERIZAÇÃO (Algoritmo do Pintor — de trás para frente):
          1. Labirinto (camada mais ao fundo)
          2. Itens especiais
          3. Inimigos
          4. Projéteis
          5. Partículas (efeitos visuais)
          6. Jogador
          7. Zona vermelha (semi-transparente, sobre tudo)
          8. HUD (interface, sempre no topo)
          9. Overlay de fim de jogo (se encerrado)
        """
        # Tela inicial: renderiza e sai imediatamente
        if self.estado == "inicio":
            desenhar_tela_inicial(tela)
            return

        # Camadas do jogo (de trás para frente)
        self.labirinto.desenhar(tela, portas=self.portas)

        for item in self.itens:
            item.desenhar(tela)

        for inimigo in self.inimigos:
            inimigo.desenhar(tela)

        for proj in self.projeteis:
            proj.desenhar(tela)

        for p in self.particulas:
            p.desenhar(tela)

        self.jogador.desenhar(tela)

        # Zona vermelha por cima de tudo (semi-transparente)
        self.zona.desenhar(tela)

        # HUD sempre visível durante a partida
        if self.estado == "jogando":
            self.hud.desenhar(tela, self)

        # Overlay de resultado ao encerrar
        if self.estado == "fim":
            eliminacoes = sum(1 for e in self.inimigos if not e.vivo)
            desenhar_tela_fim(
                tela,
                self.hud.fonte_grande,
                self.hud.fonte_media,
                self.hud.fonte_pequena,
                vitoria      = self.vitoria,
                pontuacao    = self.pontuacao,
                recorde      = self.recorde,
                segundos     = self.segundos_decorridos,
                eliminacoes  = eliminacoes,
                total        = self.total_inimigos,
                precisao     = self.jogador.precisao,
                numero_sessao= self.numero_sessao,
            )
