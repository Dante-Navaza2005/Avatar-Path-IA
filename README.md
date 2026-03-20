# Avatar Path IA

Implementação do trabalho `INF1771_IA_Trabalho_1_2026.1.pdf` usando:

- `A*` para encontrar o menor custo entre checkpoints consecutivos no mapa.
- otimização inteira exata para escolher a melhor combinação de personagens em cada etapa, respeitando o limite de `8` usos por personagem.
- visualização simples no terminal para acompanhar o deslocamento do agente.

## Estrutura

- `main.py`: ponto de entrada da aplicação.
- `avatar_path/`: código-fonte principal.
- `config/default_config.json`: mapa, custos de terreno, ordem das etapas, dificuldades e agilidade dos personagens.
- `Instrucoes/`: PDF do enunciado e mapa fornecidos.

## Como executar

Crie um ambiente com Python 3.11+ e instale a dependência:

```bash
python3 -m pip install -r requirements.txt
```

Se o seu Python for o `python@3.14` do Homebrew e a GUI reclamar de `_tkinter`, instale o suporte ao Tk:

```bash
brew install python-tk@3.14
```

Rode a solução padrão:

```bash
python3 main.py
```

O modo padrão usa `--search auto`, compara `A*`, `Dijkstra` e `Greedy`, e mantém o melhor resultado com desempate a favor de `A*` para continuar aderente ao PDF.

Para ver a comparação explicitamente:

```bash
python3 main.py --compare-search
```

Para abrir a interface gráfica:

```bash
python3 main.py --gui
```

Para visualizar os movimentos no terminal:

```bash
python3 main.py --animate
```

## Configurabilidade

Tudo que o enunciado pede como configurável está em `config/default_config.json`:

- caminho do mapa;
- custo dos terrenos;
- ordem dos checkpoints;
- dificuldade das etapas;
- agilidade e energia máxima dos personagens;
- parâmetros da visualização.

## Assunções necessárias

O PDF tem uma inconsistência entre `0`, `1` e `Z` ao falar de início, fim e dificuldade. A implementação adota:

- `0` como início da jornada, sem custo de etapa;
- as etapas com dificuldade são `1..Z`;
- `Z` possui dificuldade `310`.

Também foi adotado:

- custo `1` para entrar em uma célula de checkpoint;
- bloqueio de checkpoints futuros durante cada busca `A*`, para garantir que a ordem das etapas seja respeitada.

Ambas as escolhas podem ser alteradas no arquivo de configuração.

## Resultado padrão

Com o mapa `Instrucoes/MAPA_LENDA-AANG.txt` e a configuração padrão:

- custo total de movimento: `2807`
- custo total das etapas: `1805.548602`
- custo total final: `4612.548602`

## Testes

```bash
python3 -m unittest discover -s tests
```
