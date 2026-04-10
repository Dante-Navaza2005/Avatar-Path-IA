# Avatar Path IA

Implementacao do trabalho `INF1771_IA_Trabalho_1_2026.1.pdf` usando:

- `A*` para encontrar o menor custo entre checkpoints consecutivos no mapa.
- otimizacao inteira exata para escolher a melhor combinacao de personagens em cada etapa, respeitando o limite de `8` usos por personagem.
- visualizacao simples no terminal para acompanhar o deslocamento do agente.

## Estrutura

- `main.py`: ponto de entrada da aplicacao.
- `avatar_path/`: codigo-fonte principal.
- `config/default_config.json`: mapa, custos de terreno, ordem das etapas, dificuldades e agilidade dos personagens.
- `Instrucoes/`: PDF do enunciado e mapa fornecidos.

## Como executar

Crie um ambiente com Python 3.11+ e instale a dependencia:

```bash
python3 -m pip install -r requirements.txt
```

Se o seu Python for o `python@3.14` do Homebrew e a GUI reclamar de `_tkinter`, instale o suporte ao Tk:

```bash
brew install python-tk@3.14
```

Rode a solucao padrao:

```bash
python3 main.py
```

O modo padrao mantem a ordem fixa dos checkpoints do enunciado.

Para ver a comparacao explicitamente:

```bash
python3 main.py --compare-search
```

Para abrir a interface grafica:

```bash
python3 main.py --gui
```

Para visualizar os movimentos no terminal:

```bash
python3 main.py --animate
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

- custo total do A*: `1806`
- custo total da combinatoria: `1805.5486`
- custo total final: `3611.5486`

## Testes

```bash
python3 -m unittest discover -s tests
```
