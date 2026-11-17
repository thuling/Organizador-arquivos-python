# Organizador de Arquivos

[![CI](https://github.com/thuling/Organizador-arquivos-python/actions/workflows/ci.yml/badge.svg)](https://github.com/thuling/Organizador-arquivos-python/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

Aplicativo desktop e ferramenta de linha de comando (CLI) em Python para organizar pastas automaticamente por extensão — com **interface moderna (tema claro/escuro)**, **pré-visualização antes de mover (dry-run)**, **desfazer instantâneo**, **monitoramento em tempo real (`watchdog`)**, **regras personalizáveis** e **executável standalone (`.exe`) para Windows**.

---

## Principais recursos

- **Interface moderna em PySide6:**
  - Temas **Escuro** e **Claro** com ícones vetoriais SVG.
  - **Drag & Drop** (arraste e solte uma pasta direto na janela) + atalhos rápidos (`Downloads`, `Documentos`, `Área de Trabalho`).
  - **Pré-visualização ao vivo** com filtro de busca e contagem por categoria antes de mover qualquer arquivo.
  - **Filtro por categorias** com chips interativos e barra de progresso assíncrona.
  - **Editor visual de regras** para criar, renomear ou personalizar categorias e extensões (`config.json`).
  - **Bandeja do sistema (System Tray)** quando o monitoramento em tempo real está ativo.
- **Segurança em primeiro lugar:**
  - Extensões *case-insensitive* (`.PNG`, `.png`, `.PDF` funcionam igual) e suporte a extensões compostas (`.tar.gz`, `.tar.bz2`, `.tar.xz`).
  - Ignora subpastas (mesmo com ponto no nome), arquivos ocultos e downloads em andamento (`.crdownload`, `.part`, `.tmp`, `.download`, `.partial`).
  - Colisões de nomes resolvidas de forma legível (`documento (1).pdf`, `documento (2).pdf`).
  - Tratamento de erro por arquivo: um arquivo bloqueado/aberto não interrompe o restante do lote.
  - **Desfazer (`undo`):** restaura os arquivos movidos para a origem e remove pastas vazias criadas pela organização.
- **CLI completa + Monitoramento contínuo:** execute direto do terminal, integre em scripts ou deixe monitorando sua pasta `Downloads`.

---

## Categorias padrão

| Pasta destino | Extensões incluídas |
|---|---|
| `Imagens` | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.ico`, `.jfif`, `.heic`, `.tiff`, `.raw` |
| `Documentos` | `.pdf`, `.doc`, `.docx`, `.txt`, `.md`, `.rtf`, `.odt`, `.csv`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.epub` |
| `Áudios e Vídeos` | `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`, `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.wmv` |
| `Compactados` | `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz` |
| `Executáveis` | `.exe`, `.msi`, `.bat`, `.cmd`, `.ps1`, `.apk`, `.appimage` |
| `Código e Dados` | `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.html`, `.css`, `.json`, `.xml`, `.yaml`, `.yml`, `.sql`, `.ipynb` |
| `Outros` | Demais extensões não listadas acima (opcional, ativado por padrão) |

### Exemplo de resultado

Antes:

```text
Downloads/
├── foto.PNG
├── contrato.pdf
├── aula.mp4
├── backup.tar.gz
├── instalador.exe
└── script.py
```

Depois:

```text
Downloads/
├── Imagens/
│   └── foto.PNG
├── Documentos/
│   └── contrato.pdf
├── Áudios e Vídeos/
│   └── aula.mp4
├── Compactados/
│   └── backup.tar.gz
├── Executáveis/
│   └── instalador.exe
└── Código e Dados/
    └── script.py
```

---

## Instalação e uso (modo desenvolvimento)

### 1. Clone o repositório e crie o ambiente virtual

```bash
git clone https://github.com/thuling/Organizador-arquivos-python.git
cd Organizador-arquivos-python
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

Para rodar testes, linter e gerar o `.exe`, instale também as dependências de desenvolvimento:

```bash
pip install -r requirements-dev.txt
```

### 3. Execute a interface gráfica

```bash
python app.py
```

Ou já abrindo uma pasta específica:

```bash
python app.py --gui --path ~/Downloads
```

### 4. Uso via linha de comando (CLI)

```bash
# Simular sem mover nada (dry-run)
python app.py --path ~/Downloads --dry-run

# Organizar uma pasta
python app.py --path ~/Downloads

# Organizar apenas categorias específicas, ignorando 'Outros'
python app.py --path ~/Downloads --categories "Imagens,Documentos" --no-others

# Desfazer a última organização da pasta
python app.py --path ~/Downloads --undo

# Monitorar a pasta em tempo real (Ctrl+C para encerrar)
python app.py --path ~/Downloads --watch
```

---

## Gerar o executável (`.exe`) para Windows

Com as dependências de desenvolvimento instaladas:

```bash
pyinstaller --noconfirm --clean organizador.spec
```

O executável standalone será gerado em:

```text
dist/OrganizadorArquivos.exe
```

Basta dar um duplo clique em `OrganizadorArquivos.exe` para abrir a interface gráfica — sem precisar de Python instalado na máquina de destino.

---

## Estrutura do projeto

```text
Organizador-arquivos-python/
├── app.py                     # Ponto de entrada (GUI por padrão ou CLI com flags)
├── organizador.spec           # Especificação PyInstaller para gerar o .exe
├── pyproject.toml             # Configuração de pacote, pytest e ruff
├── assets/
│   ├── app.ico                # Ícone multi-resolução do executável
│   └── app.png
├── scripts/
│   └── generate_icon.py       # Script gerador dos ícones
├── src/organizador/
│   ├── config.py              # Regras padrão e persistência em config.json
│   ├── core.py                # Planejamento (dry-run) e execução segura
│   ├── fs_utils.py            # Resolução incremental de colisões
│   ├── history.py             # Histórico JSON e operação de desfazer
│   ├── watcher.py             # Monitoramento em tempo real com watchdog
│   ├── cli.py                 # Parser argparse e execução CLI
│   └── gui/
│       ├── icons.py           # Ícones SVG inline HiDPI
│       ├── theme.py           # Design system QSS (temas Dark e Light)
│       ├── widgets.py         # DropZone, ToggleSwitch, CategoryPill e ConfigDialog
│       └── main_window.py     # Janela principal, Worker e System Tray
└── tests/                     # Suíte automatizada com pytest
```

---

## Testes e qualidade de código

```bash
# Linter
ruff check src tests app.py

# Testes (em ambiente headless/CI no Linux use QT_QPA_PLATFORM=offscreen)
pytest -v
```

---

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
