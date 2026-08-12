# tilemap.py: labirinto (grade de tiles + mobília)

import pygame
import math
import random
from config import (
    LAYOUT_MAPA, LINHAS_MAPA, COLUNAS_MAPA, TAMANHO_TILE,
    COR_PAREDE, COR_BORDA_PAREDE, COR_PISO, COR_PISO_ALT,
    COR_BRILHO_PISCINA, COR_DEMARCACAO_PISO, DEMARCACOES_PISO,
    SPRITE_PAREDE, SPRITE_PAREDE_CLARA, SPRITE_TANQUE,
    SPRITE_CONSOLE, SPRITE_PAINEL, SPRITE_CAIXA, SPRITE_LIQUIDO_RADIOATIVO,
    SPRITE_ESTANTE_QUIMICA,
    SPRITE_PAINEL_PEQUENO, SPRITE_PAINEL_ALERTA, SPRITE_SERVIDOR, SPRITE_ARMARIO,
    SPRITE_GRADE_VERMELHA, SPRITE_PLACA_RADIACAO, SPRITE_BANCADA_QUIMICA,
    TILES_DECORATIVOS,
)

# Tiles andáveis na grade; a colisão fina da mobília é tratada à parte (ver em  _construir_retangulos_mobilia)
TILES_PASSAVEIS = ('.', 'p', 'D') + tuple(TILES_DECORATIVOS.keys())


class Labirinto:
    """
    Representa e renderiza o labirinto do jogo.

    Pré-renderiza piso e paredes em uma Surface estática (eficiência).
    Mobiliário e portas são desenhados por cima a cada frame, pois podem
    ter animações (portas) ou efeitos visuais (brilho dos tanques).
    """

    def __init__(self):
        self.largura_pixels = COLUNAS_MAPA * TAMANHO_TILE
        self.altura_pixels  = LINHAS_MAPA  * TAMANHO_TILE
        self.superficie     = pygame.Surface((self.largura_pixels, self.altura_pixels))

        # Carrega os sprites de tile (com transparência) 
        self.img_parede       = self._carregar(SPRITE_PAREDE)
        self.img_parede_clara = self._carregar(SPRITE_PAREDE_CLARA)
        self.img_tanque       = self._carregar(SPRITE_TANQUE)       
        self.img_console      = self._carregar(SPRITE_CONSOLE)      
        self.img_painel       = self._carregar(SPRITE_PAINEL)        
        self.img_caixa        = self._carregar(SPRITE_CAIXA)        
        self.img_liquido      = self._carregar(SPRITE_LIQUIDO_RADIOATIVO)  

        
        self.img_painel_pequeno  = self._carregar(SPRITE_PAINEL_PEQUENO) 
        self.img_painel_alerta   = self._carregar(SPRITE_PAINEL_ALERTA)  
        self.img_servidor        = self._carregar(SPRITE_SERVIDOR)       
        self.img_armario         = self._carregar(SPRITE_ARMARIO)        
        self.img_bancada_quimica = self._carregar(SPRITE_BANCADA_QUIMICA)
        self.img_estante_quimica = self._carregar(SPRITE_ESTANTE_QUIMICA)  

        # Área Contaminada
        self.img_grade_vermelha = self._carregar(SPRITE_GRADE_VERMELHA)
        self.img_placa_radiacao = self._carregar(SPRITE_PLACA_RADIACAO)

        # Tabela de sprites usada na renderização e na colisão da mobília
        self.sprites_mobilia = {
            "tanque":             self.img_tanque,
            "console":            self.img_console,
            "painel":             self.img_painel,
            "estante_quimica":    self.img_estante_quimica,
            "painel_pequeno":     self.img_painel_pequeno,
            "painel_alerta":      self.img_painel_alerta,
            "servidor":           self.img_servidor,
            "armario":            self.img_armario,
            "grade_vermelha":     self.img_grade_vermelha,
            "placa_radiacao":     self.img_placa_radiacao,
            "caixa":              self.img_caixa,
            "bancada_quimica":    self.img_bancada_quimica,
        }

        # Mobília do mapa, lida do LAYOUT_MAPA (fonte única de verdade)
        self.mobilia = self._construir_mobilia_do_layout()

        # Timer usado para animar o brilho pulsante da piscina radioativa
        self.timer_piscina = 0.0

        # Gotas de vazamento
        self.gotas_vazamento = []

        # Lista de retângulos de colisão de toda a mobília (tanques, console...)
        self.retangulos_mobilia = self._construir_retangulos_mobilia()

        # Pré-renderiza piso e paredes
        self._pre_renderizar()

    @staticmethod
    def _carregar(caminho):
        """
        Carrega uma imagem com suporte a transparência (convert_alpha).
        Retorna None se o arquivo não existir, permitindo fallback visual.
        """
        try:
            return pygame.image.load(caminho).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None

    # PRÉ-RENDERIZAÇÃO DO PISO E PAREDES
    def _pre_renderizar(self):
        """
        Desenha piso e paredes na surface interna (chamado uma única vez).
        O piso usa um xadrez escuro e sutil; as paredes usam o sprite do
        tileset, com uma variante mais clara no perímetro do mapa.
        """
        self.superficie.fill(COR_PISO)

        for linha in range(LINHAS_MAPA):
            for coluna in range(COLUNAS_MAPA):
                x    = coluna * TAMANHO_TILE
                y    = linha  * TAMANHO_TILE
                rect = pygame.Rect(x, y, TAMANHO_TILE, TAMANHO_TILE)
                tile = LAYOUT_MAPA[linha][coluna]

                if tile == '#':
                    self._desenhar_parede(x, y, rect, linha, coluna)
                else:
                    cor = COR_PISO_ALT if (linha + coluna) % 2 == 0 else COR_PISO
                    # Micro-variação discreta: manchas de desgaste a cada ~6 tiles
                    hash_tile = (linha * 37 + coluna * 17) % 100
                    if hash_tile < 8:
                        cor = (
                            max(0, cor[0] - 4),
                            max(0, cor[1] - 4),
                            max(0, cor[2] - 6),
                        )
                    pygame.draw.rect(self.superficie, cor, rect)
                    self._desenhar_linhas_piso(x, y, linha, coluna)

        # Faixas de demarcação das pequenas estações de trabalho
        self._desenhar_demarcacoes_piso()

    def _desenhar_demarcacoes_piso(self):
        """Desenha um contorno fino ao redor de cada área em DEMARCACOES_PISO."""
        for (coluna, linha, larg_tiles, alt_tiles) in DEMARCACOES_PISO:
            x = coluna * TAMANHO_TILE
            y = linha  * TAMANHO_TILE
            largura = larg_tiles * TAMANHO_TILE
            altura  = alt_tiles  * TAMANHO_TILE
            pygame.draw.rect(
                self.superficie, COR_DEMARCACAO_PISO,
                (x + 1, y + 1, largura - 2, altura - 2), 1
            )

    def _desenhar_linhas_piso(self, x, y, linha, coluna):
        """Desenha uma linha fina e clara nas bordas superior/esquerda do tile, sugerindo placas de piso modulares."""
        cor_linha = (
            min(255, COR_PISO_ALT[0] + 14),
            min(255, COR_PISO_ALT[1] + 16),
            min(255, COR_PISO_ALT[2] + 22),
        )
        # Linha superior do tile
        pygame.draw.line(self.superficie, cor_linha, (x, y), (x + TAMANHO_TILE, y), 1)
        # Linha esquerda do tile
        pygame.draw.line(self.superficie, cor_linha, (x, y), (x, y + TAMANHO_TILE), 1)

    # Tiles de parede (coluna, linha) que recebem o sprite 'parede_clara' para destacar o laboratório principal
    PAREDES_DESTACADAS = {
        (10, 10), (11, 10), (12, 10),
        (15, 10), (16, 10), (17, 10),
    }

    def _desenhar_parede(self, x, y, rect, linha, coluna):
        """
        Desenha um tile de parede com o sprite do tileset. Paredes na
        borda do mapa e em PAREDES_DESTACADAS usam a variante clara;
        as demais usam o sprite padrão. Sem sprite, cai no fallback
        de retângulos coloridos.
        """
        na_borda = (
            linha == 0 or linha == LINHAS_MAPA - 1 or
            coluna == 0 or coluna == COLUNAS_MAPA - 1
        )
        destacada = (coluna, linha) in self.PAREDES_DESTACADAS
        sprite = self.img_parede_clara if (na_borda or destacada) else self.img_parede

        if sprite is not None:
            self.superficie.blit(sprite, (x, y))
        else:
            # Fallback: desenho procedural (caso o sprite não seja encontrado)
            pygame.draw.rect(self.superficie, COR_PAREDE, rect)
            borda = pygame.Rect(x+1, y+1, TAMANHO_TILE-2, TAMANHO_TILE-2)
            pygame.draw.rect(self.superficie, COR_BORDA_PAREDE, borda, 1)

    # MOBILIÁRIO DO LABORATÓRIO: leitura a partir do LAYOUT_MAPA
    def _construir_mobilia_do_layout(self):
        """
        Lê o LAYOUT_MAPA e cria um item de mobília para cada letra de
        TILES_DECORATIVOS encontrada. Objetos maiores que 1x1 (ex: 'T'
        1x2, 'C' 2x2) ocupam um bloco de células com a mesma letra;
        aqui detectamos o bloco inteiro e criamos um único objeto para
        ele, usando a célula superior-esquerda como origem.

        Returns:
            list[tuple]: itens no formato
            (coluna, linha_base, nome_sprite, tem_colisao, largura_tiles, altura_tiles)
        """
        mobilia = []
        consumido = set()

        for linha in range(LINHAS_MAPA):
            for coluna in range(COLUNAS_MAPA):
                if (coluna, linha) in consumido:
                    continue

                letra = LAYOUT_MAPA[linha][coluna]
                if letra not in TILES_DECORATIVOS:
                    continue

                nome, tem_colisao, larg_tiles, alt_tiles = TILES_DECORATIVOS[letra]

                # Marca todo o bloco como consumido para não duplicar o mesmo móvel
                for dl in range(alt_tiles):
                    for dc in range(larg_tiles):
                        consumido.add((coluna + dc, linha + dl))

                linha_ancora = linha + alt_tiles - 1   # linha da base do objeto
                mobilia.append((coluna, linha_ancora, nome, tem_colisao, larg_tiles, alt_tiles))

        return mobilia

    # MOBILIÁRIO DO LABORATÓRIO: retângulos de colisão
    def _construir_retangulos_mobilia(self):
        """
        Constrói os retângulos de colisão da mobília (a partir de
        self.mobilia). A colisão é levemente menor que o sprite visual
        (margem de 4px) para o jogador não esbarrar antes de tocar o
        objeto visualmente.

        Returns:
            list[pygame.Rect]: retângulos de colisão em pixels
        """
        retangulos = []
        margem = 4

        for (coluna, linha, _sprite, tem_colisao, larg_tiles, alt_tiles) in self.mobilia:
            if not tem_colisao:
                continue
            x = coluna * TAMANHO_TILE
            # Móveis com altura > 1 crescem para cima a partir da linha-base
            y = (linha - (alt_tiles - 1)) * TAMANHO_TILE
            largura = larg_tiles * TAMANHO_TILE
            altura  = alt_tiles  * TAMANHO_TILE
            retangulos.append(pygame.Rect(
                x + margem, y + margem,
                largura - margem * 2, altura - margem * 2
            ))

        return retangulos

    # RENDERIZAÇÃO POR FRAME
    def desenhar(self, tela, portas=None):
        """
        Renderiza o labirinto: piso/paredes pré-renderizados, piscina
        radioativa, sombras da mobília, mobília e por fim as portas
        automáticas (se fornecidas).

        Args:
            tela   : pygame.Surface principal
            portas : lista opcional de objetos PortaAutomatica (door.py)
        """
        tela.blit(self.superficie, (0, 0))

        self._desenhar_nucleo_contaminacao(tela)
        self._desenhar_sombras_mobilia(tela)
        self._desenhar_mobilia(tela)

        if portas:
            for porta in portas:
                porta.desenhar(tela)

    def _desenhar_nucleo_contaminacao(self, tela):
        """Desenha a piscina radioativa (tiles 'p') com brilho verde pulsante e os vazamentos (tiles 'v')."""
        self.timer_piscina += 1
        pulso = (math.sin(self.timer_piscina * 0.05) + 1) / 2   # 0..1

        for linha in range(LINHAS_MAPA):
            for coluna in range(COLUNAS_MAPA):
                tile = LAYOUT_MAPA[linha][coluna]
                x = coluna * TAMANHO_TILE
                y = linha  * TAMANHO_TILE

                if tile == 'p':
                    if self.img_liquido is not None:
                        tela.blit(self.img_liquido, (x, y))
                    else:
                        pygame.draw.rect(tela, (20, 80, 40),
                                         (x, y, TAMANHO_TILE, TAMANHO_TILE))
                    # Brilho verde pulsante: núcleo da contaminação
                    alpha = int(30 + 35 * pulso)
                    brilho = pygame.Surface((TAMANHO_TILE, TAMANHO_TILE), pygame.SRCALPHA)
                    brilho.fill((*COR_BRILHO_PISCINA, alpha))
                    tela.blit(brilho, (x, y))

                elif tile == 'v':
                    self._desenhar_vazamento(tela, x, y, pulso)

        self._atualizar_gotas_vazamento(tela)

    def _desenhar_vazamento(self, tela, x, y, pulso):
        """Desenha uma mancha de vazamento radioativo, mais sutil que a piscina principal, na base dos tanques."""
        mancha = pygame.Surface((TAMANHO_TILE, TAMANHO_TILE), pygame.SRCALPHA)
        alpha = int(20 + 15 * pulso)
        pygame.draw.ellipse(mancha, (*COR_BRILHO_PISCINA, alpha),
                             (4, 10, TAMANHO_TILE - 8, TAMANHO_TILE - 14))
        tela.blit(mancha, (x, y))

        # Gera gotas ocasionalmente, caindo em direção à piscina
        if random.random() < 0.01:
            self.gotas_vazamento.append({
                "x": x + TAMANHO_TILE / 2,
                "y": y + TAMANHO_TILE / 2,
                "vida": 1.0,
            })

    def _atualizar_gotas_vazamento(self, tela):
        """Atualiza e desenha as gotas de vazamento, pequenos pontos verdes que descem em direção à piscina."""
        gotas_vivas = []
        for gota in self.gotas_vazamento:
            gota["y"]    += 0.6
            gota["vida"] -= 0.012
            if gota["vida"] > 0:
                gotas_vivas.append(gota)
                alpha = int(180 * gota["vida"])
                pygame.draw.circle(
                    tela, (*COR_BRILHO_PISCINA, alpha),
                    (int(gota["x"]), int(gota["y"])), 2
                )
        self.gotas_vazamento = gotas_vivas

    def _desenhar_sombras_mobilia(self, tela):
        """Desenha uma sombra elíptica na base de cada móvel com colisão, antes dos sprites (dá sensação de profundidade)."""
        for (coluna, linha, _sprite, tem_colisao, larg_tiles, alt_tiles) in self.mobilia:
            if not tem_colisao:
                continue
            largura = larg_tiles * TAMANHO_TILE
            x = coluna * TAMANHO_TILE
            # Sombra ancorada na base do objeto (linha indicada = base)
            y_base = (linha + 1) * TAMANHO_TILE

            sombra = pygame.Surface((largura, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (0, 0, 0, 90), (0, 0, largura, 14))
            tela.blit(sombra, (x, y_base - 10))

    def _desenhar_mobilia(self, tela):
        """Desenha toda a mobília do mapa (self.mobilia). Tanques recebem um brilho verde sutil pulsante."""
        pulso = (math.sin(self.timer_piscina * 0.04) + 1) / 2  # 0..1

        for (coluna, linha, nome_sprite, _colisao, larg_tiles, alt_tiles) in self.mobilia:
            sprite = self.sprites_mobilia.get(nome_sprite)
            x = coluna * TAMANHO_TILE
            y = (linha - (alt_tiles - 1)) * TAMANHO_TILE

            if sprite is not None:
                tela.blit(sprite, (x, y))
            else:
                largura = larg_tiles * TAMANHO_TILE
                altura  = alt_tiles  * TAMANHO_TILE
                pygame.draw.rect(tela, (60, 90, 70), (x, y, largura, altura))

            # Brilho verde pulsante apenas nos tanques de experimento
            if nome_sprite == "tanque" and sprite is not None:
                alpha = int(10 + 20 * pulso)
                brilho = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                pygame.draw.ellipse(brilho, (*COR_BRILHO_PISCINA, alpha),
                                    (4, 8, sprite.get_width() - 8, sprite.get_height() - 16))
                tela.blit(brilho, (x, y))

    # SISTEMA DE COLISÃO: métodos estáticos (chamados sem criar objeto)
    @staticmethod
    def e_parede(coluna, linha):
        """
        Retorna True se o tile (coluna, linha) bloqueia movimento.

        Apenas '#' bloqueia na grade. Tiles 'D' (porta) e 'p' (piscina)
        são sempre passáveis — portas nunca impedem a passagem (apenas
        animam visualmente) e a piscina é puramente decorativa.

        Células fora dos limites do mapa são tratadas como parede.
        """
        if coluna < 0 or linha < 0 or coluna >= COLUNAS_MAPA or linha >= LINHAS_MAPA:
            return True
        return LAYOUT_MAPA[linha][coluna] not in TILES_PASSAVEIS

    @staticmethod
    def pixel_para_tile(px, py):
        """Converte coordenadas de pixel para índice de tile (coluna, linha)."""
        return int(px // TAMANHO_TILE), int(py // TAMANHO_TILE)

    @staticmethod
    def tile_para_pixel_centro(coluna, linha):
        """Retorna o centro de um tile em pixels. Usado para posicionar entidades."""
        return (
            coluna * TAMANHO_TILE + TAMANHO_TILE / 2,
            linha  * TAMANHO_TILE + TAMANHO_TILE / 2
        )

    def circulo_colide_parede(self, cx, cy, raio):
        """
        Verifica se um círculo colide com paredes ou mobiliário sólido.

        Testa 8 pontos ao redor do círculo contra a grade de paredes e,
        em seguida, o retângulo delimitador do círculo contra os
        retângulos de colisão da mobília.

        Args:
            cx, cy (float): centro do círculo em pixels
            raio   (int)  : raio em pixels

        Returns:
            bool: True se há colisão com parede ou mobília
        """
        r = raio - 1   # Margem para não grudar na borda
        pontos = [
            (cx - r,       cy      ),
            (cx + r,       cy      ),
            (cx,           cy - r  ),
            (cx,           cy + r  ),
            (cx - r*0.7,   cy - r*0.7),
            (cx + r*0.7,   cy - r*0.7),
            (cx - r*0.7,   cy + r*0.7),
            (cx + r*0.7,   cy + r*0.7),
        ]
        for px, py in pontos:
            col, lin = Labirinto.pixel_para_tile(px, py)
            if Labirinto.e_parede(col, lin):
                return True

        # Colisão com mobiliário (tanques, console, painel, caixas)
        retangulo_entidade = pygame.Rect(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        for retangulo in self.retangulos_mobilia:
            if retangulo.colliderect(retangulo_entidade):
                return True

        return False
