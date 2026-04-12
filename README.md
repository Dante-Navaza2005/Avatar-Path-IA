# Avatar Path IA

## Video da apresentacao

- Link do video: `inserir_link_aqui`

## Integrantes

- `Breno de Andrade Soares` - Matricula: `2320363`
- `Dante` - Matricula: `XXXXXXXXX`
- `Rafael Soares Estevão` - Matricula: `2320470`

Implementacao do trabalho `INF1771_IA_Trabalho_1_2026.1.pdf` usando:

- `A*` para encontrar o menor custo entre checkpoints consecutivos no mapa.
- `Algoritmo Genetico + Hill Climbing + Simulated Annealing` para escolher a melhor combinacao de personagens em cada etapa, respeitando o limite de `8` usos por personagem.
- `Interface grafica (GUI)` para acompanhar o deslocamento do agente no mapa.

## Estrutura

- `main.py`: ponto de entrada da aplicacao e configuracao dos modos de execucao.
- `avatar_path/`: logica principal de planejamento, busca e carregamento do mapa.
- `avatar_path/gui.py`: inicializacao da interface grafica.
- `avatar_path/ui/`: componentes da GUI, incluindo tema, canvas do mapa e animacoes.
- `avatar_path/visualization.py`: animacao simples no terminal.
- `config/default_config.json`: mapa, custos de terreno, ordem das etapas, dificuldades e agilidade dos personagens.
- `Instrucoes/`: PDF do enunciado e mapa fornecidos.

## Como executar

Crie um ambiente com Python 3.11+:

```bash
python -m venv .venv
```

Se quiser ativar o ambiente no PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Para rodar no terminal:

```bash
python main.py
```

Para abrir a interface grafica:

```bash
python main.py --gui
```

Para visualizar os movimentos no terminal:

```bash
python main.py --animate
```

Para comparar `A*`, `Dijkstra` e `Greedy` antes da execucao:

```bash
python main.py --compare-search
```

Para escolher automaticamente o melhor algoritmo entre os disponiveis no mapa atual:

```bash
python main.py --search auto
```

## Configurabilidade

Tudo que o enunciado pede como configuravel esta em `config/default_config.json`:

- caminho do mapa;
- custo dos terrenos;
- ordem dos checkpoints;
- dificuldade das etapas;
- agilidade e energia maxima dos personagens;
- parametros da visualizacao.

## Resultado

Com o mapa `Instrucoes/MAPA_LENDA-AANG.txt`:

- custo total do A*: `2798.000000`
- custo total da combinatoria: `1805.548602`
- custo total final: `4603.548602`
