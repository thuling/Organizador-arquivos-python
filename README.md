
# Organizador de Arquivos com PYTHON

Este é um projeto de organização de arquivos em Python que permite categorizar e mover arquivos com base em suas extensões. O script utiliza a biblioteca Tkinter para exibir um diálogo de seleção de pasta, permitindo que você escolha a pasta que deseja organizar.


## Como usar

# Organizador de arquivos em Python

Este repositório contém um código em Python que organiza arquivos em pastas de acordo com suas extensões. O código é simples e fácil de usar, e pode ser usado para organizar qualquer pasta de arquivos.

## Como usar

Para usar o organizador, siga estas etapas:

1. Clone o repositório para sua máquina.
2. Abra o arquivo `organizador.py` em um editor de texto.
3. Na linha 12, insira o caminho da pasta que você deseja organizar.
4. Salve o arquivo.
5. No terminal, navegue até o diretório onde o arquivo `organizador.py` está localizado.
6. Execute o seguinte comando:

```python: 
python organizador.py
```
O organizador categoriza os arquivos em diferentes pastas com base nas seguintes extensões:

* Imagens: .jfif, .jpeg, .JPG, .png, .jpg
* Documentos: .pdf, .docx
* Áudios e Vídeos: .mp3, .mp4
* Arquivos Zipados: .zip, .rar, .7z
* Executáveis: .exe

Suponha que você tenha uma pasta chamada downloads com os seguintes arquivos:

arquivo.pdf
imagem.jpg
musica.mp3
video.mp4
exemplo.exe

Após executar o organizador, os arquivos ficarão organizados da seguinte forma:

downloads
├── img 
│   └── imagem.jpg
├── arquivos
│   └── arquivo.pdf
└── audios e videos
    ├── musica.mp3
    └── video.mp4
└── zipados
    └── exemplo.exe
