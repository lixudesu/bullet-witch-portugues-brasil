# Bullet Witch Português Brasil

Tradução comunitária não oficial da versão Steam de *Bullet Witch* para português do Brasil. O projeto trabalha sobre os textos ingleses do jogo. A tradução ainda está em fase inicial.

## Tradução por IA — ainda sem revisão

Estou usando o **GPT Astra** para ajudar na engenharia reversa dos arquivos de texto, na extração das falas e na tradução para PT-BR. Esse trabalho envolve estudar o formato dos textos e criar ferramentas de extração e reinserção; não é uma descompilação completa do jogo.

A tradução atual é **MTL (Machine Translation, ou tradução automática)**, gerada com IA e **ainda sem revisão humana**. Pode conter erros de sentido, contexto, termos e naturalidade. A revisão será feita aos poucos, com o tempo e com a ajuda da comunidade, usando os CSVs deste repositório.

## Estado atual

- `BW1_0100.bin`: cena de abertura traduzida. São 16 falas em duas tabelas internas de legendas.
- `rtevent.bin`: uma fala traduzida como teste; 168 linhas extraídas aguardam tradução e revisão.
- As legendas traduzidas foram vistas no jogo, mas a sincronização, os acentos e as demais cenas ainda precisam de revisão.

Os CSVs em `translation/` são os arquivos para tradução e revisão pública. As ferramentas em `tools/` geram arquivos `.bin` modificados a partir dos originais fornecidos por quem possui o jogo.

## Gerar os patches localmente

1. Use a versão Steam 1.0.5 do jogo. Copie **apenas** `data/text/BW1_0100.bin` e `data/text/rtevent.bin` da sua instalação para `source-original/data/text/` neste projeto.
2. Execute na pasta do projeto:

   ```powershell
   python tools/build_bw1_0100_patch.py
   python tools/build_rtevent_patch.py
   ```

3. Os arquivos gerados ficam em `patch/data/text/`. Faça backup dos dois `.bin` originais da instalação, copie os gerados para o mesmo caminho no jogo e selecione o idioma **inglês**.

As ferramentas conferem as strings originais e rejeitam traduções que excedam o espaço disponível. Elas preservam o tamanho dos arquivos, mas não corrigem a sincronização das legendas do jogo.

Para estudar mais falas de `rtevent.bin`, execute `python tools/extract_rtevent.py`. A extração sai em `build/rtevent-extracted.csv` para não sobrescrever o CSV com traduções.

## Colaborar na revisão

Edite somente a coluna `pt_br` dos CSVs, mantendo offsets, identificadores e textos de referência. Use UTF-8 e preserve as quebras de linha. Frases compridas podem ultrapassar o limite em bytes da string original; o gerador informa a linha ou offset a encurtar. Envie correções por pull request ou issue, citando o arquivo e a linha.

Este repositório não contém executáveis, vídeos, áudio, fontes nem os arquivos `.bin` originais ou modificados do jogo. *Bullet Witch* pertence aos seus respectivos titulares. O projeto não é afiliado aos criadores ou à editora.
